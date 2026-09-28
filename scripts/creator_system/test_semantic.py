"""Synthetic Markdown only; structural checks never claim semantic truth."""
import copy
from pathlib import Path
import tempfile
import unittest

from creator_system.semantic import prepare_document, pack_fingerprint, validate_analysis, validate_review, compare_documents, static_findings
from creator_system.store import canonical, digest


class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.path=self.root/'draft.md'
        self.path.write_text('---\ntitle: Test title\n---\n# Main\n\nFirst actual sentence.\n\nSecond actual sentence.\n')
        self.source=self.root/'source.md';self.source.write_text('---\nid: SRC-1\n---\nProvided source note, not checked original.')
        self.pack=prepare_document(self.path,[self.source])
        self.body=[b for b in self.pack['blocks'] if b['kind']!='heading']
        self.analysis=self.analysis_for(self.pack)

    def tearDown(self):self.tmp.cleanup()

    def analysis_for(self,pack):
        body=[b for b in pack['blocks'] if b['kind']!='heading']; heading=[b['id'] for b in pack['blocks'] if b['kind']=='heading']
        return {'schema':1,'document_sha256':pack['document']['sha256'],'pack_sha256':pack_fingerprint(pack),'segments':[
            {'id':f'S-{i}','title':'Segment','role':'explanation','question':'What is asserted?','thesis':block['text'],
             'claim_type':'factual','audience_before':'Has a question','audience_after':'Knows the stated answer',
             'source_blocks':[block['id']],'context_blocks':heading,'reasoning_steps':[],
             'evidence':[{'source_id':'SRC-1','relation':'supports','scope':'Provided note only'}], 'limitations':[],
             'visuals':[{'id':f'V-{i}','type':'statement','purpose':'Display the stated sentence','source_blocks':[block['id']]}]}
            for i,block in enumerate(body)],'exclusions':[]}

    def review_for(self):
        bid=self.body[0]['id']
        return {'schema':1,'document_sha256':self.pack['document']['sha256'],'analysis_sha256':digest(canonical(self.analysis).encode()),
                'reviewer':{'kind':'ai','name':'Synthetic independent reviewer'},'strengths':['Clear source anchors'],
                'findings':[{'id':'F-1','segment_ids':['S-0'],'block_ids':[bid],'category':'evidence','severity':'minor',
                             'observation':'Need original context','reason':'Only a supplied note is attached','impact':'Scope remains uncertain',
                             'options':['Attach the actual original passage'],'uncertainty':'The original source was not read',
                             'status':'open','anchors':[{'block_id':bid,'quote':'First actual sentence.'}]}]}

    def test_original_lines_frontmatter_and_no_automatic_source_verification(self):
        self.assertEqual(self.pack['document']['title'],'Test title')
        self.assertEqual((self.body[0]['line_start'],self.body[0]['line_end']),(6,6))
        self.assertEqual(self.body[0]['text'],'First actual sentence.')
        self.assertEqual(self.pack['sources'][0]['provenance'],'provided_source_note')
        self.assertNotIn('verified',self.pack['sources'][0].get('status',''))
        report=validate_analysis(self.pack,self.analysis)
        self.assertTrue(report['valid']);self.assertEqual(report['coverage']['ratio'],1)
        self.assertFalse(report['author_approved']);self.assertFalse(report['semantic_verified'])

    def test_unknown_block_source_duplicate_ids_and_transition(self):
        for field,value in [('source_blocks',['missing']),('evidence',[{'source_id':'MISSING','relation':'supports','scope':'x'}]),('transition',{'to':'missing','reason':'because'})]:
            analysis=copy.deepcopy(self.analysis);analysis['segments'][0][field]=value
            self.assertFalse(validate_analysis(self.pack,analysis)['valid'])
        for target in ('segment','visual'):
            analysis=copy.deepcopy(self.analysis)
            if target=='segment':analysis['segments'][1]['id']='S-0'
            else:analysis['segments'][1]['visuals'][0]['id']='V-0'
            self.assertFalse(validate_analysis(self.pack,analysis)['valid'])

    def test_missing_and_double_body_ownership_with_shared_headings_allowed(self):
        missing=copy.deepcopy(self.analysis);missing['segments'].pop()
        self.assertEqual(validate_analysis(self.pack,missing)['coverage']['unassigned_block_ids'],[self.body[1]['id']])
        duplicate=copy.deepcopy(self.analysis);duplicate['segments'][1]['source_blocks'].append(self.body[0]['id'])
        self.assertFalse(validate_analysis(self.pack,duplicate)['valid'])
        for segment in self.analysis['segments']:segment['source_blocks'].append(self.pack['blocks'][0]['id'])
        self.assertTrue(validate_analysis(self.pack,self.analysis)['valid'])

    def test_review_literal_anchor_stale_bindings_and_resolution_actor(self):
        review=self.review_for();self.assertTrue(validate_review(self.pack,self.analysis,review)['valid'])
        forged=copy.deepcopy(review);forged['findings'][0]['anchors'][0]['quote']='Invented sentence.'
        self.assertFalse(validate_review(self.pack,self.analysis,forged)['valid'])
        stale=copy.deepcopy(review);stale['analysis_sha256']='old'
        self.assertFalse(validate_review(self.pack,self.analysis,stale)['valid'])
        self.analysis['document_sha256']='old'
        self.assertFalse(validate_analysis(self.pack,self.analysis)['valid'])
        self.analysis['document_sha256']=self.pack['document']['sha256']
        resolved=copy.deepcopy(review);resolved['findings'][0]['status']='resolved'
        self.assertFalse(validate_review(self.pack,self.analysis,resolved)['valid'])
        resolved['findings'][0]['resolution']={'actor':'Declared editor','reason':'Added original context'}
        result=validate_review(self.pack,self.analysis,resolved)
        self.assertTrue(result['valid']);self.assertFalse(result['author_approved'])

    def test_insert_does_not_renumber_unchanged_blocks_but_changes_neighbors(self):
        self.path.write_text(self.path.read_text().replace('First actual sentence.','New insertion.\n\nFirst actual sentence.'))
        new=prepare_document(self.path,[self.source]);delta=compare_documents(self.pack,new,self.analysis)
        self.assertTrue(all(b['id'] in {x['id'] for x in new['blocks']} for b in self.pack['blocks']))
        self.assertEqual(delta['removed'],[]);self.assertEqual(delta['moved'],[])
        self.assertEqual(len(delta['new_unassigned_blocks']),1)
        self.assertIn(self.body[0]['id'],delta['context_changed'])
        self.assertEqual(delta['rerecord_segment_ids'],[])
        self.assertEqual(delta['affected_segment_ids'],['S-0'])

    def test_moves_and_section_changes_are_not_silent(self):
        self.path.write_text('# Main\n\nSecond actual sentence.\n\nFirst actual sentence.\n')
        new=prepare_document(self.path,[self.source]);delta=compare_documents(self.pack,new,self.analysis)
        self.assertTrue(delta['moved']);self.assertTrue(delta['affected_segment_ids'])
        self.assertEqual(delta['rerecord_segment_ids'],[])
        self.path.write_text('# A different heading\n\nFirst actual sentence.\n\nSecond actual sentence.\n')
        new=prepare_document(self.path,[self.source]);delta=compare_documents(self.pack,new,self.analysis)
        self.assertTrue(all(b['id'] in delta['context_changed'] for b in self.body))

    def test_changed_core_text_needs_rerecord_not_visual_only_change(self):
        same=copy.deepcopy(self.analysis);same['segments'][0]['visuals'][0]['purpose']='Change color layout'
        self.assertEqual(compare_documents(self.pack,self.pack,same)['rerecord_segment_ids'],[])
        self.path.write_text(self.path.read_text().replace('First actual sentence.','Revised core sentence.'))
        delta=compare_documents(self.pack,prepare_document(self.path,[self.source]),self.analysis)
        self.assertIn('S-0',delta['rerecord_segment_ids']);self.assertIn('V-0',delta['affected_visual_ids'])
        self.assertEqual(len(delta['changed']),1)

    def test_duplicate_paragraphs_are_explicitly_ambiguous(self):
        self.path.write_text('# Main\n\nRepeated.\n\nRepeated.\n')
        pack=prepare_document(self.path,[self.source]);body=[b for b in pack['blocks'] if b['kind']!='heading']
        self.assertNotEqual(body[0]['id'],body[1]['id']);self.assertTrue(all(b['ambiguous'] for b in body))
        delta=compare_documents(pack,pack,self.analysis_for(pack))
        self.assertEqual(set(delta['ambiguous_duplicate']),{b['id'] for b in body})

    def test_source_note_change_stales_analysis_review_and_dependents(self):
        review=self.review_for()
        self.source.write_text('---\nid: SRC-1\n---\nChanged provided source note.')
        new=prepare_document(self.path,[self.source])
        self.assertEqual(self.pack['document']['sha256'],new['document']['sha256'])
        self.assertFalse(validate_analysis(new,self.analysis)['valid'])
        self.assertFalse(validate_review(new,self.analysis,review)['valid'])
        delta=compare_documents(self.pack,new,self.analysis)
        self.assertEqual(delta['source_changed_ids'],['SRC-1'])
        self.assertEqual(delta['affected_segment_ids'],['S-0','S-1'])
        self.assertEqual(delta['rerecord_segment_ids'],[])

    def test_static_signals_never_claim_argument_weakness_or_true_verdict(self):
        self.analysis['segments'][0]['claim_type']='causal';self.analysis['segments'][0]['evidence']=[]
        self.analysis['segments'][0]['visuals'][0]['nodes']=['x']*9
        signals=static_findings(self.pack,self.analysis)
        self.assertEqual({x['code'] for x in signals},{'causal_without_steps','source_claim_without_evidence','many_visual_nodes'})
        self.assertTrue(all(x['provenance']=='program_signal_needs_review' and x['semantic_verdict'] is None for x in signals))


if __name__=='__main__':unittest.main()
