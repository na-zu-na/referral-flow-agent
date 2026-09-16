import inspect
import json
import unittest

from tools import (
    DESCRIPTORS,
    DESCRIPTORS_V1,
    DESCRIPTORS_V2,
    REGISTRY,
    call_tool,
    get_descriptors,
)


class ToolDescriptorTests(unittest.TestCase):
    required_fields = {
        "name",
        "signature",
        "what",
        "input",
        "returns",
        "fails_when",
        "irreversible",
    }

    def test_every_registered_tool_has_a_complete_descriptor(self):
        self.assertEqual(set(DESCRIPTORS), set(REGISTRY))
        for name, descriptor in DESCRIPTORS.items():
            with self.subTest(tool=name):
                self.assertEqual(set(descriptor), self.required_fields)
                self.assertEqual(descriptor["name"], name)
                self.assertIn(name + "(", descriptor["signature"])
                self.assertEqual(
                    descriptor["irreversible"]["value"],
                    "yes" if name == "book_slot" else "no",
                )
                self.assertTrue(descriptor["irreversible"]["gate"])
                self.assertEqual(set(descriptor["returns"]), {"shape", "size_bound"})
                self.assertTrue(descriptor["returns"]["size_bound"])
                for argument in descriptor["input"].values():
                    self.assertIn("type", argument)
                    self.assertIn("required", argument)
                    self.assertIn("constraints", argument)
                    self.assertIn("bad_value", argument)
                json.dumps(descriptor)

    def test_descriptor_arguments_match_function_signatures(self):
        for name, function in REGISTRY.items():
            with self.subTest(tool=name):
                self.assertEqual(
                    set(DESCRIPTORS[name]["input"]),
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

        for required in (
            "specialty",
            "band",
            "window",
            "capacity_remaining",
            "no_slot",
            "1..20",
        ):
            self.assertIn(required, text)

    def test_slot_v1_and_v2_return_shapes_are_really_different(self):
        arguments = {
            "specialty": "OPH",
            "band": "routine",
            "window_start": "2026-09-09",
            "window_end": "2026-11-04",
            "limit": 5,
        }

        v1 = call_tool("get_clinic_slots", arguments, descriptor_version="v1")
        v2 = call_tool("get_clinic_slots", arguments, descriptor_version="v2")

        self.assertTrue(v1["ok"] and v2["ok"])
        self.assertEqual(set(v1["data"]), {"result", "slots"})
        self.assertEqual(
            set(v2["data"]), {"result", "requested_window", "slots"}
        )
        self.assertEqual(v1["data"]["slots"], v2["data"]["slots"])

    def test_unknown_return_contract_is_rejected(self):
        result = call_tool("get_referral", {"referral_id": "REF-5602"}, descriptor_version="v3")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "INVALID_DESCRIPTOR_VERSION")

    def test_get_descriptors_returns_a_copy_and_rejects_unknown_versions(self):
        selected = get_descriptors("v2")
        selected["get_referral"]["what"] = "changed"

        self.assertNotEqual(
            selected["get_referral"]["what"],
            DESCRIPTORS["get_referral"]["what"],
        )
        with self.assertRaises(ValueError):
            get_descriptors("v3")


if __name__ == "__main__":
    unittest.main()
