"""Shared household facts survive channels without changing device pages or task records."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from hub.household import Household, ScopeError, _exchange


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.vault = Path(self.tmp.name) / 'vault'
        (self.vault / 'Tasks/tasks').mkdir(parents=True)
        self.state = Path(self.tmp.name) / 'state'
        self.h = Household(self.vault, None, self.state)

    def saved(self):
        return self.h.remember('fact-1', 'House inventory: lightbulbs', 'Three spare lightbulbs are in the hall closet.')

    def path(self):
        return next((self.vault / 'References/Catthew').glob('*.md'))

    def test_fact_is_durable_and_searchable_from_another_channel_instance(self):
        note = self.saved()
        telegram = Household(self.vault, None, self.state)
        found = telegram.search_notes('lightbulbs')
        self.assertTrue(note['ok'])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['id'], note['id'])
        self.assertEqual(found[0]['revision'], note['revision'])
        self.assertTrue(found[0]['managed_memory'])
        self.assertIn('hall closet', found[0]['text'])
        self.assertEqual(self.h.tasks(), [])
        self.assertEqual(self.h.groceries()['items'], [])
        self.assertEqual(list((self.vault / 'Tasks/tasks').iterdir()), [])

    def test_matching_end_of_memory_returns_the_whole_fact_for_safe_edits(self):
        content = 'Important inventory detail. ' * 30 + 'Stored in basement.'
        saved = self.h.remember('long', 'Inventory details', content)
        self.assertEqual(self.h.search_notes('basement')[0]['text'], saved['text'])

    def test_retries_deduplicate_and_changed_payload_is_rejected(self):
        first = self.saved()
        self.assertEqual(self.saved(), first)
        with self.assertRaises(ScopeError):
            self.h.remember('fact-1', 'House inventory: lightbulbs', 'Different location')
        self.assertEqual(len(list((self.vault / 'References/Catthew').glob('*.md'))), 1)

    def test_update_requires_current_revision_and_preserves_history(self):
        first = self.saved()
        changed = self.h.update_memory(first['id'], first['revision'], 'The spare lightbulbs moved to the basement.')
        self.assertNotEqual(first['revision'], changed['revision'])
        with self.assertRaises(ScopeError):
            self.h.update_memory(first['id'], first['revision'], 'An old location')
        found = Household(self.vault, None, self.state).search_notes('lightbulbs')[0]
        self.assertIn('basement', found['text'])
        history = list((self.path().parent / '.catthew-history').glob('*.md'))
        self.assertEqual(len(history), 1)
        self.assertIn('hall closet', history[0].read_text())
        with self.assertRaises(ScopeError):
            self.saved()

    def test_other_tagged_reference_notes_are_read_only(self):
        p = self.vault / 'family.md'
        p.write_text('---\ntitle: Original guide\ntags: [kittyggup]\n---\nLightbulbs are fragile.\n')
        before = p.read_bytes()
        note = self.h.search_notes('lightbulbs')[0]
        self.assertFalse(note['managed_memory'])
        with self.assertRaises(ScopeError):
            self.h.update_memory(note['id'], note['revision'], 'Replace an unrelated record')
        self.assertEqual(p.read_bytes(), before)

    def test_reference_directory_and_note_symlinks_are_refused(self):
        outside = Path(self.tmp.name) / 'outside'
        outside.mkdir()
        (self.vault / 'References').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ScopeError):
            self.saved()
        self.assertEqual(list(outside.iterdir()), [])
        (self.vault / 'References').unlink()
        first = self.saved()
        p = self.path()
        target = outside / 'fact.md'
        p.rename(target)
        p.symlink_to(target)
        before = target.read_bytes()
        with self.assertRaises(ScopeError):
            self.h.update_memory(first['id'], first['revision'], 'Changed')
        self.assertEqual(target.read_bytes(), before)

    def test_body_tag_does_not_authorize_memory_edits(self):
        first = self.saved()
        p = self.path()
        p.write_text(p.read_text().replace('- kittyggup', '- another') + '\n#kittyggup\n')
        note = self.h.search_notes('lightbulbs')[0]
        self.assertFalse(note['managed_memory'])
        with self.assertRaises(ScopeError):
            self.h.update_memory(first['id'], note['revision'], 'Changed')

    def test_oversized_human_memory_is_not_truncated_into_an_editable_fact(self):
        first = self.saved()
        p = self.path()
        p.write_text(p.read_text() + 'Human detail ' * 200)
        before = p.read_bytes()
        note = self.h.search_notes('lightbulbs')[0]
        self.assertFalse(note['managed_memory'])
        with self.assertRaises(ScopeError):
            self.h.update_memory(first['id'], note['revision'], 'Changed')
        self.assertEqual(p.read_bytes(), before)

    def test_racing_manual_edit_is_preserved(self):
        first = self.saved()
        p = self.path()
        original = p.read_bytes()
        calls = []
        def race(a, b):
            if not calls:
                p.write_bytes(original + b'\nConcurrent human update\n')
            calls.append(True)
            _exchange(a, b)
        with patch('hub.household._exchange', side_effect=race):
            with self.assertRaises(ScopeError):
                self.h.update_memory(first['id'], first['revision'], 'Changed')
        self.assertIn('Concurrent human update', p.read_text())

    def test_bounds_and_managed_metadata(self):
        for title, content in [('a\nInjected heading', 'fact'), ('title', 'x' * 1501), ('title', '')]:
            with self.assertRaises(ValueError):
                self.h.remember('invalid', title, content)
        first = self.saved()
        meta = yaml.safe_load(self.path().read_text().split('---', 2)[1])
        self.assertIn('kittyggup', meta['tags'])
        self.assertEqual(meta['type'], 'catthew-memory')
        for identity, revision in [('../../outside', first['revision']), (first['id'], 'stale')]:
            with self.assertRaises((ScopeError, ValueError)):
                self.h.update_memory(identity, revision, 'Changed')


if __name__ == '__main__':
    unittest.main()
