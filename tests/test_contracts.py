from pathlib import Path
import hashlib
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import core

class ArtifactContracts(unittest.TestCase):
    def test_source_and_artifact_digests(self):
        manifest = json.loads((ROOT / "results/manifest.json").read_text())
        for rel, digest in manifest["source_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), digest, rel)
        for rel, digest in manifest["artifact_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / "results" / rel).read_bytes()).hexdigest(), digest, rel)

    def test_generator_reproduces_committed_inputs(self):
        self.assertEqual(core.generate(), json.loads((ROOT / "data/dataset.json").read_text()))

import tempfile

class DocumentationContracts(unittest.TestCase):
    def test_known_parameter_kinds_and_none_default(self):
        source="def f(a, /, b=None, *args, required, c=1, **options) -> int: pass"
        signature=core.extract(source)['f']
        self.assertEqual(['positional_only','positional_or_keyword','var_positional','keyword_only','keyword_only','var_keyword'],[p['kind'] for p in signature['parameters']])
        self.assertTrue(signature['parameters'][1]['has_default'])
        self.assertEqual('None',signature['parameters'][1]['default'])
        self.assertFalse(signature['parameters'][3]['has_default'])

    def test_parsing_does_not_execute_top_level_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker=Path(tmp)/'never-created'
            source=f"open({str(marker)!r}, 'w').write('bad')\nraise RuntimeError('not executed')\ndef f(): pass\n"
            self.assertIn('f',core.extract(source))
            self.assertFalse(marker.exists())

    def test_default_drift_missed_by_symbol_only_control(self):
        old='def f(x=1): pass';new='def f(x=2): pass';docs=core.extract(old)
        self.assertEqual('matched',core.audit(new,docs,False)['status'])
        self.assertEqual('drift',core.audit(new,docs,True)['status'])

    def test_async_and_argument_kind_are_part_of_contract(self):
        docs=core.extract('async def f(*, x): pass')
        self.assertEqual('drift',core.audit('def f(x): pass',docs)['status'])

    def test_dynamic_exports_and_decorators_require_review(self):
        for source in ['__all__=get_exports()\ndef f(): pass', '@wrapper\ndef f(): pass', 'from unknown import *\ndef f(): pass']:
            with self.subTest(source=source):self.assertEqual('manual_review',core.audit(source,{})['status'])

    def test_export_mutation_and_redefinition_require_review(self):
        for source in ["__all__=['f']\n__all__.append('g')\ndef f(): pass", "__all__=['f']\n__all__[0]='g'\ndef f(): pass", 'def f(): pass\ndef f(x): pass']:
            with self.subTest(source=source):self.assertEqual('manual_review',core.audit(source,{})['status'])

    def test_syntax_error_is_not_claimed_as_documentation_match(self):
        self.assertEqual('manual_review',core.audit('def (',{})['status'])

    def test_conditional_export_mutations_are_not_claimed_as_matches(self):
        base=core.generate()['base_source'];docs=core.extract(base)
        for suffix in ["if True:\n    __all__.append('extra')\n", "for item in ['extra']:\n    __all__.append(item)\n", "try:\n    __all__[0]='extra'\nexcept Exception:\n    pass\n", "class Wrapper:\n    __all__.append('extra')\n", "def _change():\n    global __all__\n    __all__=[]\n"]:
            with self.subTest(suffix=suffix):self.assertEqual('manual_review',core.audit(base+'\n'+suffix,docs)['status'])
        local=base+"\ndef _helper():\n    __all__=['local']\n    return __all__\n"
        self.assertEqual('matched',core.audit(local,docs)['status'])

    def test_all_original_mutations_replay_saved_decisions(self):
        data=core.generate();raw=json.loads((ROOT/'results/decisions.json').read_text())
        for case,row in zip(data['cases'],raw):
            result=core.audit(case['source'],data['documented_manifest'])
            self.assertEqual(row['signature_aware'],result)
            self.assertEqual(case['expected_status'],result['status'])
