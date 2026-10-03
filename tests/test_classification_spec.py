import unittest

from app.services.turn_service import classify_intent


class SpecificationClassificationTests(unittest.TestCase):
    def test_build_spec_open_door_example_is_classified_as_mechanical(self):
        self.assertEqual(classify_intent("Eu abro a porta."), "mechanical_likely")

    def test_common_physical_actions_are_classified_as_mechanical(self):
        for text in (
            "Eu arrombo o baú.",
            "Eu escalo o muro.",
            "Eu me escondo nas sombras.",
            "Eu tento persuadir o guarda.",
            "I open the door.",
        ):
            with self.subTest(text=text):
                self.assertEqual(classify_intent(text), "mechanical_likely")

    def test_plain_dialogue_label_is_advisory_not_a_rule_engine_bypass(self):
        self.assertEqual(
            classify_intent("Converso com o mercador sobre a viagem."),
            "narrative_or_unknown",
        )


if __name__ == "__main__":
    unittest.main()
