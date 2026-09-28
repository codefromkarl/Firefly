"""Deterministic document/semantic-candidate contracts; never fabricates semantic judgments."""
from __future__ import annotations

from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
import re
import yaml

from .store import ControlError, canonical, digest

ROLES = {'hook','definition','explanation','comparison','example','boundary','application','conclusion','transition'}
CLAIM_TYPES = {'definition','factual','causal','comparison','recommendation','personal_judgment','none'}
CATEGORIES = {'evidence','logic','scope','definition','transition','presentation','coverage'}
SEVERITIES = {'major','minor','suggestion'}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _read(path):
    if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*://', str(path)):
        raise ControlError('Only explicitly provided local Markdown files are read')
    path = Path(path).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() not in {'.md','.markdown'}:
        raise ControlError('Expected a local Markdown file')
    value = path.read_bytes()
    try:
        text = value.decode('utf-8-sig')
    except UnicodeError as error:
        raise ControlError('Markdown must be UTF-8') from error
    return path, value, text


def _frontmatter(lines):
    if not lines or lines[0].strip() != '---':
        return {}, 0
    end = next((i for i in range(1,len(lines)) if lines[i].strip() == '---'), None)
    if end is None:
        raise ControlError('Unclosed Markdown frontmatter')
    try:
        meta = yaml.safe_load('\n'.join(lines[1:end])) or {}
    except yaml.YAMLError as error:
        raise ControlError('Invalid Markdown frontmatter') from error
    if not isinstance(meta, dict):
        raise ControlError('Markdown frontmatter must be a mapping')
    return meta, end + 1


def prepare_document(path, source_paths=None):
    path, raw, text = _read(path)
    lines = text.splitlines()
    meta, index = _frontmatter(lines)
    blocks, counts, headings = [], Counter(), {}
    title = meta.get('title') if _text(meta.get('title')) else None
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        start = index
        heading = re.match(r'^(#{1,6})\s+(.+?)\s*$', lines[index])
        fence = re.match(r'^\s*(`{3,}|~{3,})', lines[index])
        if heading:
            kind = 'heading'
            level = len(heading[1])
            headings = {depth: value for depth,value in headings.items() if depth < level}
            heading_text = re.sub(r'\s+#+\s*$', '', heading[2])
            headings[level] = heading_text
            if title is None:
                title = heading_text
            index += 1
        elif fence:
            kind = 'code'
            marker = fence[1]
            index += 1
            while index < len(lines):
                current = lines[index]
                index += 1
                if re.match(r'^\s*' + re.escape(marker[0]) + '{' + str(len(marker)) + r',}\s*$', current):
                    break
        else:
            kind = ('list' if re.match(r'^\s*(?:[-+*]|\d+[.)])\s+', lines[index]) else
                    'quote' if re.match(r'^\s*>', lines[index]) else 'paragraph')
            index += 1
            while index < len(lines) and lines[index].strip() and not re.match(r'^(#{1,6})\s+', lines[index]) and not re.match(r'^\s*(`{3,}|~{3,})', lines[index]):
                index += 1
        content = '\n'.join(lines[start:index])
        sha = digest(content.encode())
        counts[sha] += 1
        blocks.append({'id':f'B-{sha[:20]}-{counts[sha]}','ordinal':len(blocks)+1,'kind':kind,
                       'section':' / '.join(headings[k] for k in sorted(headings)), 'text':content,
                       'sha256':sha,'line_start':start+1,'line_end':index})
    for block in blocks:
        block['ambiguous'] = counts[block['sha256']] > 1
    sources, source_ids = [], set()
    for source_path in source_paths or []:
        source_path, value, content = _read(source_path)
        source_meta, _ = _frontmatter(content.splitlines())
        source_id = source_meta.get('id') or 'SRC-' + digest(value)[:20]
        if not _text(source_id) or source_id in source_ids:
            raise ControlError('Provided source notes need unique string IDs')
        source_ids.add(source_id)
        sources.append({'id':source_id,'sha256':digest(value),'content':content,'path':str(source_path),
                        'provenance':'provided_source_note','verification':'not_automatically_primary_verified'})
    return {'schema':1,'document':{'sha256':digest(raw),'title':title or path.stem,'path':str(path)},
            'blocks':blocks,'sources':sources,'provenance':'deterministic_layout_blocks_not_semantic_analysis'}


def pack_fingerprint(pack):
    """Bind exact document blocks and all supplied-source identities/content/paths."""
    if not isinstance(pack, dict):
        raise ControlError('Document pack must be an object')
    return digest(canonical({key:value for key,value in pack.items() if key != 'captured_at'}).encode())


def _pack_errors(pack):
    if not isinstance(pack,dict) or pack.get('schema') != 1 or not isinstance(pack.get('document'),dict) or not _text(pack['document'].get('sha256')) or not isinstance(pack.get('blocks'),list):
        return ['Invalid document pack schema']
    errors, ids, occurrences = [], set(), Counter()
    for block in pack['blocks']:
        if not isinstance(block,dict) or not _text(block.get('id')) or not isinstance(block.get('text'),str):
            errors.append('Invalid document block'); continue
        if block['id'] in ids:
            errors.append('Duplicate block ID: '+block['id'])
        ids.add(block['id'])
        if block.get('kind') not in {'heading','paragraph','list','quote','code'} or not isinstance(block.get('section'),str):
            errors.append('Block kind/section missing or invalid: '+block['id'])
        if any(isinstance(block.get(key),bool) or not isinstance(block.get(key),int) or block[key]<1 for key in ('ordinal','line_start','line_end')):
            errors.append('Block ordinal/original line coordinates invalid: '+block['id'])
        elif block['line_end'] < block['line_start']:
            errors.append('Block line coordinates reversed: '+block['id'])
        computed = digest(block['text'].encode())
        occurrences[computed] += 1
        if computed != block.get('sha256'):
            errors.append('Block text/hash mismatch: '+block['id'])
        if block['id'] != f'B-{computed[:20]}-{occurrences[computed]}':
            errors.append('Block stable identity mismatch: '+block['id'])
    sources=pack.get('sources',[])
    if not isinstance(sources,list):
        errors.append('Provided sources must be a list')
    else:
        source_ids=set()
        for source in sources:
            if not isinstance(source,dict) or not _text(source.get('id')) or not _text(source.get('sha256')) or not isinstance(source.get('content'),str):
                errors.append('Invalid provided source record');continue
            if source['id'] in source_ids:errors.append('Duplicate provided source ID: '+source['id'])
            source_ids.add(source['id'])
    return errors


def validate_analysis(pack, analysis):
    errors, warnings = _pack_errors(pack), []
    result = {'status':'pending_review','valid':False,'errors':errors,'warnings':warnings,
              'coverage':{},'semantic_verified':False,'author_approved':False}
    if errors:
        return result
    if not isinstance(analysis,dict) or analysis.get('schema') != 1 or not isinstance(analysis.get('segments'),list) or not isinstance(analysis.get('exclusions',[]),list):
        errors.append('Invalid analysis schema'); return result
    try:
        result['analysis_sha256'] = digest(canonical(analysis).encode())
    except (ValueError,TypeError):
        errors.append('Analysis must contain finite JSON values'); return result
    if analysis.get('pack_sha256') != pack_fingerprint(pack):
        errors.append('Analysis document/source pack fingerprint is stale or missing')
    if analysis.get('document_sha256') != pack['document']['sha256']:
        errors.append('Analysis document hash is stale')
    blocks = {b['id']:b for b in pack['blocks']}
    sources = {s['id'] for s in pack.get('sources',[])}
    segment_ids, visual_ids, ownership, excluded = set(), set(), defaultdict(list), set()
    transitions = []
    def block_refs(value,label):
        if not isinstance(value,list) or not all(_text(x) for x in value):
            errors.append(label+' must be a block ID list'); return []
        if len(value) != len(set(value)):
            errors.append(label+' repeats a block ID')
        for block_id in value:
            if block_id not in blocks:
                errors.append(label+' contains unknown block '+block_id)
        return value
    for segment in analysis['segments']:
        if not isinstance(segment,dict):
            errors.append('Segment must be an object'); continue
        sid = segment.get('id')
        if not _text(sid) or sid in segment_ids:
            errors.append('Segment ID missing or duplicated: '+str(sid)); continue
        segment_ids.add(sid)
        for field in ('title','question','thesis','audience_before','audience_after'):
            if not _text(segment.get(field)):
                errors.append(f'{sid}.{field} must be explicit nonempty text')
        if segment.get('role') not in ROLES: errors.append(sid+'.role invalid')
        if segment.get('claim_type') not in CLAIM_TYPES: errors.append(sid+'.claim_type invalid')
        core = block_refs(segment.get('source_blocks'),sid+'.source_blocks')
        if not core: errors.append(sid+' requires at least one actual source block')
        context = block_refs(segment.get('context_blocks',[]),sid+'.context_blocks')
        for bid in core:
            if bid in blocks and blocks[bid]['kind'] != 'heading': ownership[bid].append(sid)
        for field in ('reasoning_steps','limitations'):
            if not isinstance(segment.get(field,[]),list) or not all(_text(value) for value in segment.get(field,[])): errors.append(f'{sid}.{field} must be a list of nonempty text')
        evidence = segment.get('evidence',[])
        if not isinstance(evidence,list): errors.append(sid+'.evidence must be a list'); evidence=[]
        for link in evidence:
            if not isinstance(link,dict) or not _text(link.get('source_id')) or link['source_id'] not in sources:
                errors.append(sid+' evidence references an unknown provided source'); continue
            if not _text(link.get('relation')) or not _text(link.get('scope')):
                errors.append(sid+' evidence needs an explicit relation and scope')
        visuals = segment.get('visuals',[])
        if not isinstance(visuals,list): errors.append(sid+'.visuals must be a list'); visuals=[]
        for visual in visuals:
            if not isinstance(visual,dict):errors.append(sid+' visual must be an object');continue
            vid=visual.get('id')
            if not _text(vid) or vid in visual_ids:errors.append('Visual ID missing or duplicated: '+str(vid))
            else:visual_ids.add(vid)
            if not _text(visual.get('type')) or not _text(visual.get('purpose')):errors.append(str(vid)+' needs type and purpose')
            refs=block_refs(visual.get('source_blocks',[]),str(vid)+'.source_blocks')
            if not refs:errors.append(str(vid)+' requires an actual source block')
            if not set(refs) <= set(core+context):errors.append(str(vid)+' uses blocks outside its declared segment/context')
        transition=segment.get('transition')
        if transition is not None:
            if not isinstance(transition,dict) or not _text(transition.get('to')) or not _text(transition.get('reason')):errors.append(sid+' transition requires to and reason')
            else:transitions.append((sid,transition['to']))
    for sid,target in transitions:
        if target not in segment_ids or target==sid:errors.append(sid+' transition points to an unknown or identical segment')
    for exclusion in analysis.get('exclusions',[]):
        if not isinstance(exclusion,dict) or not _text(exclusion.get('block_id')) or exclusion['block_id'] not in blocks or not _text(exclusion.get('reason')):
            errors.append('Exclusion needs existing block and explicit reason');continue
        bid=exclusion['block_id']
        if bid in excluded:errors.append('Duplicate exclusion: '+bid)
        excluded.add(bid)
        if bid in ownership:errors.append('Block is both assigned and excluded: '+bid)
    body={b['id'] for b in pack['blocks'] if b['kind']!='heading'}
    missing=sorted(body-set(ownership)-excluded)
    duplicated={bid:ids for bid,ids in ownership.items() if len(ids)>1}
    if missing:errors.append('Unassigned body blocks: '+', '.join(missing))
    if duplicated:errors.append('Body blocks assigned to multiple segments: '+', '.join(duplicated))
    ambiguous=[b['id'] for b in pack['blocks'] if b.get('ambiguous')]
    if ambiguous:warnings.append('Repeated identical text needs location/context review: '+', '.join(ambiguous))
    result['coverage']={'body_total':len(body),'covered':len(body&set(ownership)),'excluded':len(body&excluded),
                        'unassigned_block_ids':missing,'duplicated_assignments':duplicated,
                        'ratio':len(body&(set(ownership)|excluded))/len(body) if body else 1.0}
    result['valid']=not errors
    return result


def validate_review(pack, analysis, review):
    base=validate_analysis(pack,analysis)
    errors=list(base['errors']);warnings=list(base['warnings'])
    report={'status':'pending_review','valid':False,'errors':errors,'warnings':warnings,
            'semantic_verified':False,'author_approved':False,'identity_provenance':'caller_declared_not_authenticated'}
    if not isinstance(review,dict) or review.get('schema')!=1 or not isinstance(review.get('findings'),list):
        errors.append('Invalid review schema');return report
    if review.get('document_sha256')!=pack.get('document',{}).get('sha256'):errors.append('Review document hash is stale')
    if review.get('analysis_sha256')!=base.get('analysis_sha256'):errors.append('Review analysis hash is stale')
    reviewer=review.get('reviewer',{})
    if not isinstance(reviewer,dict) or reviewer.get('kind') not in {'ai','human'} or not _text(reviewer.get('name')):errors.append('Reviewer kind/name must be explicitly declared')
    if not isinstance(review.get('strengths',[]),list) or not all(_text(value) for value in review.get('strengths',[])):errors.append('Review strengths must be a list of nonempty text')
    blocks={b['id']:b for b in pack.get('blocks',[]) if isinstance(b,dict) and 'id' in b}
    segments={s.get('id'):s for s in analysis.get('segments',[]) if isinstance(s,dict)} if isinstance(analysis,dict) else {}
    ids=set()
    for finding in review['findings']:
        if not isinstance(finding,dict):errors.append('Finding must be an object');continue
        fid=finding.get('id')
        if not _text(fid) or fid in ids:errors.append('Finding ID missing or duplicated: '+str(fid));continue
        ids.add(fid)
        if finding.get('category') not in CATEGORIES or finding.get('severity') not in SEVERITIES:errors.append(fid+' has invalid category/severity')
        for field in ('observation','reason','impact','uncertainty'):
            if not _text(finding.get(field)):errors.append(fid+'.'+field+' must be explicit text')
        options=finding.get('options')
        if not isinstance(options,list) or not options or not all(_text(x) for x in options):errors.append(fid+' needs concrete text options')
        sids=finding.get('segment_ids',[]);bids=finding.get('block_ids',[])
        if not isinstance(sids,list) or not sids or not all(isinstance(x,str) and x in segments for x in sids):errors.append(fid+' requires at least one existing segment');sids=[]
        if not isinstance(bids,list) or not bids or not all(isinstance(x,str) and x in blocks for x in bids):errors.append(fid+' requires existing block IDs');bids=[]
        anchors=finding.get('anchors')
        if not isinstance(anchors,list) or not anchors:errors.append(fid+' needs at least one literal original-text anchor');anchors=[]
        for anchor in anchors:
            if not isinstance(anchor,dict) or not _text(anchor.get('block_id')) or anchor['block_id'] not in blocks or not _text(anchor.get('quote')):
                errors.append(fid+' has invalid anchor');continue
            bid=anchor['block_id']
            if bid not in bids or anchor['quote'] not in blocks[bid]['text']:errors.append(fid+' anchor quote or block identity does not literally match')
            if sids and not any(bid in segments[s].get('source_blocks',[])+segments[s].get('context_blocks',[]) for s in sids):errors.append(fid+' anchor is unrelated to declared segments')
        status=finding.get('status')
        if status not in {'open','resolved','dismissed'}:errors.append(fid+' status invalid')
        if status in {'resolved','dismissed'}:
            resolution=finding.get('resolution')
            if not isinstance(resolution,dict) or not _text(resolution.get('reason')) or not (_text(resolution.get('actor')) or isinstance(resolution.get('actor'),dict) and _text(resolution['actor'].get('name'))):errors.append(fid+' resolution requires declared reason and actor; it is not author approval')
    report['valid']=not errors
    report['open_findings']=[f['id'] for f in review['findings'] if isinstance(f,dict) and f.get('status')=='open' and _text(f.get('id'))]
    return report


def static_findings(pack, analysis):
    validation=validate_analysis(pack,analysis)
    findings=[]
    def add(code,segment_ids,block_ids,observation):
        findings.append({'id':f'SIGNAL-{len(findings)+1:03}','code':code,'segment_ids':segment_ids,'block_ids':block_ids,
                         'observation':observation,'provenance':'program_signal_needs_review','semantic_verdict':None})
    for bid in validation.get('coverage',{}).get('unassigned_block_ids',[]):add('unassigned_body',[],[bid],'Body block has no declared segment or reasoned exclusion.')
    for segment in analysis.get('segments',[]) if isinstance(analysis,dict) else []:
        if not isinstance(segment,dict):continue
        sid=segment.get('id');bids=segment.get('source_blocks',[])
        if segment.get('claim_type')=='causal' and not segment.get('reasoning_steps'):add('causal_without_steps',[sid],bids,'Declared causal claim has no recorded reasoning steps; semantic adequacy is unknown.')
        if segment.get('claim_type') in {'factual','causal','comparison'} and not segment.get('evidence'):add('source_claim_without_evidence',[sid],bids,'Declared source-based claim has no recorded evidence links; inspect original argument and sources.')
        visuals=segment.get('visuals',[])
        if isinstance(visuals,list):
            for visual in visuals:
                if isinstance(visual,dict) and isinstance(visual.get('nodes'),list) and len(visual['nodes'])>5:
                    add('many_visual_nodes',[sid],bids,f"Visual {visual.get('id')} has {len(visual['nodes'])} nodes, beyond the current renderer's 5-node limit; split the picture, not the argument by default.")
    return findings


def compare_documents(old_pack, new_pack, analysis):
    for pack in (old_pack,new_pack):
        errors=_pack_errors(pack)
        if errors:raise ControlError('; '.join(errors))
    if not isinstance(analysis,dict) or analysis.get('document_sha256') != old_pack['document']['sha256'] or analysis.get('pack_sha256') != pack_fingerprint(old_pack):
        raise ControlError('Comparison analysis must be bound to the old document/source pack')
    old={b['id']:b for b in old_pack['blocks']};new={b['id']:b for b in new_pack['blocks']}
    old_ids=list(old);new_ids=list(new);common=set(old)&set(new)
    added=[bid for bid in new_ids if bid not in old];removed=[bid for bid in old_ids if bid not in new]
    old_common=[bid for bid in old_ids if bid in common];new_common=[bid for bid in new_ids if bid in common]
    new_positions={bid:i for i,bid in enumerate(new_common)}
    moved=[bid for i,bid in enumerate(old_common) if new_positions[bid]!=i]
    def context(blocks):
        return {block['id']:(block.get('section'),blocks[i-1]['id'] if i else None,blocks[i+1]['id'] if i+1<len(blocks) else None) for i,block in enumerate(blocks)}
    before=context(old_pack['blocks']);after=context(new_pack['blocks'])
    changed_context=[bid for bid in old_ids if bid in common and before[bid]!=after[bid]]
    replacements=[]
    for opcode,a,b,c,d in SequenceMatcher(a=old_ids,b=new_ids,autojunk=False).get_opcodes():
        if opcode=='replace':
            for prior,later in zip(old_ids[a:b],new_ids[c:d]):
                if prior in removed and later in added:
                    replacements.append({'old_id':prior,'new_id':later,'basis':'structural_alignment_candidate_not_semantic_equivalence'})
    ambiguous=sorted({b['id'] for p in (old_pack,new_pack) for b in p['blocks'] if b.get('ambiguous')})
    old_sources={s['id']:s['sha256'] for s in old_pack.get('sources',[])}
    new_sources={s['id']:s['sha256'] for s in new_pack.get('sources',[])}
    source_changed_ids=sorted(sid for sid in old_sources.keys()|new_sources.keys() if old_sources.get(sid)!=new_sources.get(sid))
    # Shared headings keep their textual/section context when only the first body
    # paragraph below them changes; do not invalidate every distant segment.
    propagated_context=[bid for bid in changed_context if old[bid]['kind']!='heading' or old[bid].get('section')!=new[bid].get('section')]
    affected_blocks=set(removed+moved+propagated_context+ambiguous)
    affected_segments,affected_visuals,rerecord,assigned=[],[],[],set()
    for segment in analysis.get('segments',[]):
        core=set(segment.get('source_blocks',[]));context_ids=set(segment.get('context_blocks',[]))
        assigned.update(core)
        evidence_changed=any(e.get('source_id') in source_changed_ids for e in segment.get('evidence',[]) if isinstance(e,dict))
        if (core|context_ids)&affected_blocks or evidence_changed:affected_segments.append(segment['id'])
        if core&set(removed):rerecord.append(segment['id'])
        for visual in segment.get('visuals',[]):
            if set(visual.get('source_blocks',[]))&affected_blocks or context_ids&affected_blocks or evidence_changed:affected_visuals.append(visual['id'])
    excluded={x.get('block_id') for x in analysis.get('exclusions',[]) if isinstance(x,dict)}
    return {'status':'pending_review','document_changed':old_pack['document']['sha256']!=new_pack['document']['sha256'],
            'added':added,'removed':removed,'changed':replacements,'moved':moved,'context_changed':changed_context,
            'ambiguous_duplicate':ambiguous,'source_changed_ids':source_changed_ids,'affected_segment_ids':sorted(set(affected_segments)),
            'affected_visual_ids':sorted(set(affected_visuals)),'rerecord_segment_ids':sorted(set(rerecord)),
            'new_unassigned_blocks':[bid for bid in new_ids if new[bid]['kind']!='heading' and bid not in assigned and bid not in excluded],
            'rerecord_scope':'removed_or_changed_core_source_text_only; context changes need review, not automatic rerecord'}
