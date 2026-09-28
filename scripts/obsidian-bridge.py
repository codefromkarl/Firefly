#!/usr/bin/env python3
"""Non-overwriting Firefly → Obsidian import; private local ebook inventory."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

import yaml

PROJECT = Path(__file__).resolve().parents[1]
FOLDERS = ['00 收件箱', '10 书籍', '20 知识卡片', '30 主题研究', '40 内容项目', '50 来源', '90 模板', '99 附件']
LIBRARIES = [Path.home() / '下载/书单', Path.home() / 'Downloads/心理与人文书单']
EBOOKS = {'.epub', '.pdf', '.mobi', '.azw', '.azw3', '.txt'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def note(properties, body):
    return '---\n' + yaml.safe_dump(properties, allow_unicode=True, sort_keys=False) + '---\n\n' + body.strip() + '\n'


def book_notes(books):
    result = {}
    for source in sorted(books.glob('*/index.md')):
        text = source.read_text()
        chunks = text.split('---', 2)
        if len(chunks) != 3 or chunks[0].strip():
            raise ValueError(f'Invalid frontmatter: {source}')
        data = yaml.safe_load(chunks[1])
        slug = source.parent.name
        props = {'type': 'book', 'book_id': slug, 'title': data['title'],
                 'aliases': [data['title']], 'authors': data.get('authors', []),
                 'reading_status': data.get('status', 'unknown'),
                 'graph_stage': data.get('graphStage', 'unknown'),
                 'verification': '导入原始记录，未新增人工核实',
                 'source_kind': 'Firefly原有书单与笔记',
                 'topics': data.get('topics', []), 'shelf': data.get('shelf', ''),
                 'source_path': f'src/content/books/{slug}/index.md', 'source_sha256': digest(text.encode())}
        body = f'# {data["title"]}\n\n> 导入保留原记录及预读标记；读完状态不等于观点已复核。以下导入内容不是用户本次阅读的新判断。\n\n'
        body += '## 原书单元数据与来源\n\n```yaml\n' + chunks[1].strip() + '\n```\n\n'
        body += '## 原书单笔记\n\n' + chunks[2].strip() + '\n\n## 我的阅读与核查记录\n\n在此记录版本、章节、问题、自己的理解与核查日期。\n'
        result[f'10 书籍/{slug}.md'] = note(props, body)
    if not result:
        raise ValueError('No book records found')
    return result


def foundation():
    result = {'首页.md': '# 读书与创作\n\n[[书单.base|书单视图]] · [[阅读导航|所有书籍]] · [[创作导航|本期研究与稿件]]\n\n从 00 收件箱记录问题；在 30 主题研究建立主线；从 10 书籍及 50 来源提取 20 知识卡片；在 40 内容项目写作、导出、复盘。\n\n每个重要观点都保留来源、适用边界与反例。预读、核对文本、个人认可和公开发布分别记录。\n\n模板位于 90 模板；在设置 → 核心插件 → 模板中选择该目录。书单视图需要内置 Bases；没有启用时仍可使用阅读导航。\n',
    '书单.base': yaml.safe_dump({'filters': {'and': ['file.inFolder("10 书籍")', 'type == "book"']}, 'views': [{'type': 'table', 'name': '全部书籍', 'order': ['file.name', 'title', 'authors', 'reading_status', 'graph_stage', 'topics']}, {'type': 'table', 'name': '正在读', 'filters': 'reading_status == "reading"', 'order': ['file.name', 'title', 'authors', 'graph_stage']}]}, allow_unicode=True, sort_keys=False)}
    templates = {
        '书籍': ({'type': 'book', 'book_id': '', 'reading_status': 'unknown', 'verification': '待核查'}, '# {{title}}\n\n## 阅读问题\n\n## 版本与定位\n\n## 章节记录\n\n## 我的理解与反例'),
        '知识卡片': ({'type': 'claim', 'id': '', 'claim_type': '', 'verification': 'pending_review', 'sources': [], 'topics': []}, '# {{title}}\n\n## 主张\n\n## 证据与来源定位\n\n## 推论与作者原意的区别\n\n## 反例与适用边界\n\n## 用于哪些项目'),
        '主题研究': ({'type': 'topic', 'id': '', 'status': '研究中', 'sources': [], 'claims': []}, '# {{title}}\n\n## 观众和问题\n\n## 工作定义\n\n## 问题递进\n\n## 支持与反对的证据\n\n## 书单外待读材料\n\n## 本期取舍'),
        '来源': ({'type': 'source', 'id': '', 'source_type': 'web', 'locator': '', 'url': '', 'accessed': '', 'verification': 'pending', 'rights': '待确认'}, '# {{title}}\n\n## 作者、版本与机构\n\n## 精确定位与短摘录\n\n## 支持什么\n\n## 不支持什么\n\n## 使用范围与引用'),
        '内容项目': ({'type': 'project', 'id': '', 'status': '候选', 'publish_url': '', 'sources': [], 'claims': []}, '# {{title}}\n\n## 受众与本期承诺\n\n## 主稿与证据\n\n## 核查、排版和试看\n\n## 发布记录\n\n## 第7天/第30天反馈\n\n## 纠错与后续选题')}
    templates['主稿'] = ({'type': 'article', 'id': '', 'verification': 'pending_review', 'status': 'draft', 'sources': [], 'topics': []}, '# {{title}}\n\n写可直接公开的正文。公开来源用 HTTPS 链接；私有知识库链接只放在 frontmatter，正文不要写本地文件路径或私有 wikilinks。\n\n## 参考资料\n')
    for name, (props, body) in templates.items():
        result[f'90 模板/{name}.md'] = note(props, body)
    return result


def inventory(roots=LIBRARIES):
    started = datetime.now(timezone.utc).isoformat()
    files = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob('*')):
            if path.is_symlink() or not path.is_file() or path.suffix.lower() not in EBOOKS:
                continue
            if not path.resolve().is_relative_to(root.resolve()):
                continue
            before = path.stat()
            row = {'path': str(path), 'format': path.suffix.lower()[1:], 'bytes': before.st_size}
            h = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    h.update(chunk)
            row['sha256'] = h.hexdigest()
            row['reading_status'] = 'unknown'
            row['validation'] = 'not_checked'
            if path.suffix.lower() == '.epub':
                try:
                    with zipfile.ZipFile(path) as z:
                        # Prevent allocating enormous decompressed content; this is an integrity/metadata check.
                        if any(x.file_size > 128 * 1024 * 1024 for x in z.infolist()) or sum(x.file_size for x in z.infolist()) > 1024 * 1024 * 1024:
                            raise ValueError('archive exceeds inventory bounds')
                        bad = z.testzip()
                        if bad:
                            raise ValueError('ZIP CRC failure')
                        if z.read('mimetype').strip() != b'application/epub+zip':
                            raise ValueError('invalid EPUB mimetype')
                        container = ET.fromstring(z.read('META-INF/container.xml'))
                        package_path = container.find('.//{*}rootfile').attrib['full-path']
                        package = ET.fromstring(z.read(package_path))
                        ns = {'dc': 'http://purl.org/dc/elements/1.1/'}
                        row['title'] = [x.text for x in package.findall('.//dc:title', ns) if x.text]
                        row['authors'] = [x.text for x in package.findall('.//dc:creator', ns) if x.text]
                        row['identifiers'] = [x.text for x in package.findall('.//dc:identifier', ns) if x.text]
                        row['validation'] = 'zip_crc_container_opf_pass' # Not full epubcheck or claim verification.
                except (zipfile.BadZipFile, KeyError, ET.ParseError, ValueError, AttributeError, RuntimeError, OSError) as error:
                    row['validation'] = 'invalid_or_unreadable'
                    row['error_type'] = type(error).__name__
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                row['validation'] = 'unstable_during_scan'
                row.pop('sha256', None)
            files.append(row)
    hashes = {}
    for row in files:
        if 'sha256' in row:
            hashes.setdefault(row['sha256'], []).append(row['path'])
    return {'schema': 1, 'scan_started_at': started, 'scan_finished_at': datetime.now(timezone.utc).isoformat(), 'roots': [str(r) for r in roots], 'meaning': '文件库存，不等于作品数；元数据不是用户阅读或观点核实状态。',
            'files': files, 'byte_identical_groups': [paths for paths in hashes.values() if len(paths) > 1]}


def assert_safe(vault, relative):
    target = vault / relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Unsafe relative path')
    current = target
    while current != vault.parent:
        if current.is_symlink():
            raise ValueError(f'Symlink import target refused: {current}')
        if current == vault:
            break
        current = current.parent
    return target


def apply_files(vault, files, apply=False):
    # Preflight every collision before writing anything. Never replace an existing file.
    plan = []
    for relative, content in files.items():
        target = assert_safe(vault, relative)
        state = 'create'
        if target.exists():
            identical = target.is_file() and target.read_text() == content
            if target.is_file() and target.suffix == '.base' and not identical:
                # Obsidian rewrites YAML indentation on first open; compare meaning without writing.
                try:
                    identical = yaml.safe_load(target.read_text()) == yaml.safe_load(content)
                except yaml.YAMLError:
                    identical = False
            state = 'unchanged' if identical else 'conflict'
        plan.append({'path': relative, 'action': state})
    conflicts = [p for p in plan if p['action'] == 'conflict']
    if apply and not conflicts:
        for folder in FOLDERS:
            assert_safe(vault, folder).mkdir(parents=True, exist_ok=True)
        for row in plan:
            if row['action'] != 'create':
                continue
            target = assert_safe(vault, row['path'])
            target.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive create closes the check/write overwrite race.
            with target.open('x', encoding='utf-8') as stream:
                stream.write(files[row['path']])
    return plan, conflicts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', required=True, type=Path)
    parser.add_argument('--apply', action='store_true', help='Create only missing files; default is read-only plan')
    parser.add_argument('--inventory', action='store_true', help='Inventory only the two documented local book folders')
    parser.add_argument('--seed', type=Path, default=PROJECT / 'docs/creator-workflow/example-vault', help='Example-vault Markdown and .base files; defaults to bundled sample')
    args = parser.parse_args()
    vault = args.vault.expanduser().absolute()
    # Resolve parents as well; direct symlink vaults are refused by assert_safe.
    for parent in [vault, *vault.parents]:
        if parent.is_symlink():
            raise ValueError(f'Symlink vault ancestor refused: {parent}')
    if vault.resolve().is_relative_to(PROJECT) and not vault.resolve().is_relative_to(PROJECT / '.local'):
        raise ValueError('Private vault inside project must be under .local, never docs/src/public')
    files = foundation()
    books = book_notes(PROJECT / 'src/content/books')
    files.update(books)
    files['阅读导航.md'] = '# 书单\n\n' + '\n'.join(f'- [[{p[:-3]}|{yaml.safe_load(t.split("---", 2)[1])["title"]}]]' for p, t in books.items()) + '\n'
    if args.seed:
        if not args.seed.is_dir():
            raise ValueError('Seed directory does not exist')
        for source in sorted(args.seed.rglob('*')):
            if source.is_file() and not source.is_symlink() and source.suffix in {'.md', '.base'}:
                relative = source.relative_to(args.seed).as_posix()
                if relative in files:
                    raise ValueError(f'Seed collides with generated file: {relative}')
                files[relative] = source.read_text()
        links = [f'- [[{path[:-3]}]]' for path in sorted(files) if path.endswith('.md') and path.startswith(('30 主题研究/', '40 内容项目/'))]
        files['创作导航.md'] = '# 当前创作导航\n\n从主题进入问题主线，从项目卡进入本期研究、稿件和发布记录。\n\n' + '\n'.join(links) + '\n'
    inv = None
    if args.inventory:
        inv = inventory()
        payload = json.dumps(inv, ensure_ascii=False, indent=2) + '\n'
        # Content-addressed snapshots preserve old inventories and remain idempotent.
        snapshot = digest(payload.encode())[:12]
        files[f'50 来源/本地库存-{snapshot}.json'] = payload
        def cell(value):
            return str(value).replace('|', '\\|').replace('\n', ' ')
        lines = ['# 本地电子书文件库存', '', '这是文件库存，不是去重后的作品书单。阅读状态均未知；EPUB 检查只证明 ZIP、container 与 OPF 可读取，不代表完整 EPUB 标准校验或原文观点核实。', '', '| 文件元数据标题 | 作者 | 格式 | 完整性检查 | 原文件路径 |', '| --- | --- | --- | --- | --- |']
        for row in inv['files']:
            lines.append('| ' + ' | '.join(cell(value) for value in [', '.join(row.get('title', [])) or '未提取', ', '.join(row.get('authors', [])) or '未提取', row['format'], row['validation'], row['path']]) + ' |')
        lines.extend(['', '## 字节完全相同的副本组', '', f'共 {len(inv["byte_identical_groups"])} 组；不同哈希不代表不同作品或版本。完整 SHA-256 和副本路径见同编号 JSON。'])
        files[f'50 来源/本地库存-{snapshot}.md'] = '\n'.join(lines) + '\n'
    plan, conflicts = apply_files(vault, files, args.apply)
    summary = {'mode': 'apply' if args.apply else 'plan', 'vault': str(vault), 'books': len(books),
               'created': sum(p['action'] == 'create' for p in plan) if args.apply and not conflicts else 0,
               'planned_create': sum(p['action'] == 'create' for p in plan),
               'unchanged': sum(p['action'] == 'unchanged' for p in plan), 'conflicts': conflicts,
               'inventory_files': len(inv['files']) if inv else None,
               'inventory_invalid_epubs': sum(f['validation'] == 'invalid_or_unreadable' for f in inv['files']) if inv else None}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 2 if conflicts else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, yaml.YAMLError) as error:
        print(f'Bridge stopped: {error}', file=sys.stderr)
        sys.exit(1)
