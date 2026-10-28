import unittest
from top_mold.memory_policy import decay_weight, persistence_decision


class PersistenceDecisionTests(unittest.TestCase):
    def test_one_off_joke_is_session_only(self):
        self.assertEqual(persistence_decision("joke"), "session_only")

    def test_sensitive_data_is_not_persisted_without_permission(self):
        self.assertEqual(
            persistence_decision("explicit_preference", sensitive=True),
            "do_not_persist_without_explicit_permission",
        )

    def test_explicit_permission_can_make_durable_preference_a_candidate(self):
        self.assertEqual(
            persistence_decision("explicit_preference", explicit_permission=True),
            "durable_profile_candidate",
        )

    def test_unconfirmed_preference_waits_for_confirmation(self):
        self.assertEqual(
            persistence_decision("explicit_preference"),
            "ask_or_wait_for_confirmation",
        )

    def test_single_observation_does_not_become_hypothesis(self):
        self.assertEqual(
            persistence_decision("observed_hypothesis", evidence_count=1),
            "session_only_insufficient_repeated_evidence",
        )

    def test_repeated_observation_yields_scoped_candidate_not_fact(self):
        self.assertEqual(
            persistence_decision("observed_hypothesis", evidence_count=3, independent_context_count=2),
            "scoped_hypothesis_candidate_for_review",
        )

    def test_sensitive_inference_is_not_persisted_even_with_many_observations(self):
        self.assertEqual(
            persistence_decision("observed_hypothesis", evidence_count=10, sensitive=True, explicit_permission=True),
            "do_not_persist_sensitive_inference",
        )

    def test_deletion_request_wins_over_archival_logic(self):
        self.assertEqual(
            persistence_decision("task_state", task_active=False, user_deletion_requested=True),
            "delete_active_and_archived_copies",
        )

    def test_task_state_active_and_inactive_are_distinct(self):
        self.assertEqual(persistence_decision("task_state", task_active=True), "active_task_state")
        self.assertEqual(persistence_decision("task_state", task_active=False), "inactive_task_state_review_or_expire")

    def test_sensitive_storage_requires_permission_and_clear_purpose(self):
        self.assertEqual(
            persistence_decision("explicit_preference", sensitive=True, explicit_permission=True),
            "do_not_persist_without_clear_purpose",
        )
        self.assertEqual(
            persistence_decision("explicit_preference", sensitive=True, explicit_permission=True, clear_purpose=True),
            "durable_profile_candidate",
        )

    def test_repeated_observation_without_independent_contexts_is_not_candidate(self):
        self.assertEqual(
            persistence_decision("observed_hypothesis", evidence_count=3),
            "scoped_hypothesis_needs_independent_context_review",
        )

    def test_invalid_policy_counts_and_boolean_flags_are_rejected(self):
        with self.assertRaises(TypeError):
            persistence_decision("observed_hypothesis", evidence_count=True)
        with self.assertRaises(ValueError):
            persistence_decision("observed_hypothesis", evidence_count=-1)
        with self.assertRaises(TypeError):
            persistence_decision("explicit_preference", explicit_permission=1)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            persistence_decision("observed_hypothesis", evidence_count=2, independent_context_count=3)

    def test_sensitive_hypothesis_never_becomes_durable_from_permission(self):
        self.assertEqual(
            persistence_decision(
                "observed_hypothesis", sensitive=True, explicit_permission=True,
                clear_purpose=True, evidence_count=10, independent_context_count=5,
            ),
            "do_not_persist_sensitive_inference",
        )

    def test_external_fact_requires_source_and_validity(self):
        self.assertEqual(persistence_decision("external_fact"), "do_not_treat_as_verified_external_fact")
        self.assertEqual(persistence_decision("external_fact", source_available=True), "needs_timestamp_or_validity_review")
        self.assertEqual(
            persistence_decision("external_fact", source_available=True, validity_known=True),
            "retain_with_source_and_revalidation_date",
        )


class DecayTests(unittest.TestCase):
    def test_decay_halves_at_half_life(self):
        self.assertAlmostEqual(decay_weight("task_state", 7), 0.5)

    def test_decay_reduces_priority_not_deletion(self):
        weight = decay_weight("observed_hypothesis", 60)
        self.assertAlmostEqual(weight, 0.25)
        self.assertGreater(weight, 0.0)

    def test_durable_preference_does_not_decay_from_time_alone(self):
        self.assertEqual(decay_weight("explicit_preference", 3650), 1.0)

    def test_explicit_half_life_can_be_used_for_durable_preference(self):
        self.assertAlmostEqual(decay_weight("explicit_preference", 30, half_life_days=30), 0.5)

    def test_negative_age_rejected(self):
        with self.assertRaises(ValueError):
            decay_weight("task_state", -1)

    def test_bool_age_rejected(self):
        with self.assertRaises(TypeError):
            decay_weight("task_state", True)

    def test_nonpositive_half_life_rejected(self):
        with self.assertRaises(ValueError):
            decay_weight("task_state", 1, half_life_days=0)

    def test_nonfinite_age_and_half_life_are_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    decay_weight("task_state", value)
                with self.assertRaises(ValueError):
                    decay_weight("task_state", 1, half_life_days=value)

    def test_boolean_and_nonfinite_record_values_are_not_silently_coerced(self):
        with self.assertRaises(TypeError):
            decay_weight("task_state", True)
        with self.assertRaises(TypeError):
            decay_weight([], 1)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main(verbosity=2)
