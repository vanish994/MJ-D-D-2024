import unittest

from app.services.turn_service import classify_intent, looks_mechanical


class SpecificationClassificationTests(unittest.TestCase):
    def test_build_spec_open_door_example_routes_to_rule_engine(self):
        self.assertTrue(looks_mechanical("Eu abro a porta."))

    def test_common_physical_actions_route_to_rule_engine(self):
        for text in (
            "Eu arrombo o baú.",
            "Eu escalo o muro.",
            "Eu me escondo nas sombras.",
            "Eu tento persuadir o guarda.",
            "I open the door.",
        ):
            with self.subTest(text=text):
                self.assertTrue(looks_mechanical(text))

    def test_plain_dialogue_label_is_advisory_not_a_rule_engine_bypass(self):
        self.assertFalse(looks_mechanical("Converso com o mercador sobre a viagem."))
        self.assertEqual(
            classify_intent("Converso com o mercador sobre a viagem."),
            "narrative_or_unknown",
        )


if __name__ == "__main__":
    unittest.main()
