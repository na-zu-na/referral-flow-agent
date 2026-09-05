import inspect
import json
import unittest

from tools import DESCRIPTORS, DESCRIPTORS_V1, DESCRIPTORS_V2, REGISTRY, get_descriptors


class ToolDescriptorTests(unittest.TestCase):
    required_fields = {
        "name",
        "purpose",
        "when",
        "arguments",
        "returns",
        "failure",
        "irreversible",
    }

    def test_every_registered_tool_has_a_complete_descriptor(self):
        self.assertEqual(set(DESCRIPTORS), set(REGISTRY))
        for name, descriptor in DESCRIPTORS.items():
            with self.subTest(tool=name):
                self.assertEqual(set(descriptor), self.required_fields)
                self.assertEqual(descriptor["name"], name)
                self.assertEqual(descriptor["irreversible"], name == "book_slot")
                json.dumps(descriptor)

    def test_descriptor_arguments_match_function_signatures(self):
        for name, function in REGISTRY.items():
            with self.subTest(tool=name):
                self.assertEqual(
                    set(DESCRIPTORS[name]["arguments"]),
                    {
                        parameter
                        for parameter in inspect.signature(function).parameters
                        if not parameter.startswith("_")
                    },
                )

    def test_v1_and_v2_only_change_the_slot_descriptor(self):
        self.assertEqual(set(DESCRIPTORS_V1), set(DESCRIPTORS_V2))
        for name in DESCRIPTORS_V1:
            if name == "get_clinic_slots":
                self.assertNotEqual(DESCRIPTORS_V1[name], DESCRIPTORS_V2[name])
            else:
                self.assertEqual(DESCRIPTORS_V1[name], DESCRIPTORS_V2[name])

    def test_v2_documents_the_slot_safety_contract(self):
        text = json.dumps(DESCRIPTORS_V2["get_clinic_slots"]).lower()

        for required in ("specialty", "band", "window", "capacity_remaining", "no_slot"):
            self.assertIn(required, text)

    def test_get_descriptors_returns_a_copy_and_rejects_unknown_versions(self):
        selected = get_descriptors("v2")
        selected["get_referral"]["purpose"] = "changed"

        self.assertNotEqual(
            selected["get_referral"]["purpose"],
            DESCRIPTORS["get_referral"]["purpose"],
        )
        with self.assertRaises(ValueError):
            get_descriptors("v3")


if __name__ == "__main__":
    unittest.main()
