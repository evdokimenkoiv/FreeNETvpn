from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]


def test_bilingual_entrypoints_share_installer_and_valid_links():
    en=(ROOT/'README.md').read_text(encoding='utf-8')
    ru=(ROOT/'README.ru.md').read_text(encoding='utf-8')
    assert en.split('```bash\n',1)[1].split('\n```',1)[0]==ru.split('```bash\n',1)[1].split('\n```',1)[0]
    for relative in ['README.md','README.ru.md','docs/accounts.en.md','docs/accounts.ru.md','docs/devices.en.md','docs/devices.ru.md','docs/images/README.md']:
        file=ROOT/relative
        for target in re.findall(r'\]\(([^)]+)\)',file.read_text(encoding='utf-8')):
            if '://' not in target:
                assert (file.parent/target.split('#',1)[0]).exists(),(relative,target)
    for locale in ['en','ru']:
        text=(ROOT/f'docs/devices.{locale}.md').read_text(encoding='utf-8')
        for device in ['iOS','macOS','Windows','Android','OpenWrt']:
            assert device in text


def test_readme_screenshots_match_the_document_language():
    en=(ROOT/'README.md').read_text(encoding='utf-8')
    ru=(ROOT/'README.ru.md').read_text(encoding='utf-8')
    assert all('-en.' in p for p in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',en))
    assert all('-en.' not in p for p in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',ru))
    assert 'FREENET_REF=main;' in en and 'FREENET_REF=main;' in ru
