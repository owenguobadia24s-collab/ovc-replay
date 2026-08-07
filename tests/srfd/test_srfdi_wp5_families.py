from __future__ import annotations

import unittest

from ovc.opt_b.srfd.families import DistanceMatrix, FamilyMethodSpec, bounded_pam, family_assignments, hierarchical, medoid_star


def matrix(ids, values):
    return DistanceMatrix.from_pairs(ids,values)


class SRFDIWP5FamilyTests(unittest.TestCase):
    def test_medoid_star_is_deterministic_baseline_with_residuals(self) -> None:
        m = matrix(["D","A","C","B"],{"A|B":"0.1","A|C":"0.2","A|D":"1.0","B|C":"0.1","B|D":"1.0","C|D":"1.0"})
        spec = FamilyMethodSpec("GREEDY_LEXICOGRAPHIC_MEDOID_STAR","CFG",radius="0.25",minimum_support=2)
        first = medoid_star(m,spec); second = medoid_star(matrix(reversed(m.ids),m.values),spec)
        self.assertEqual(first,second)
        self.assertEqual(1,len(first["families"])); self.assertEqual(["D"],first["residual_ids"])
        self.assertEqual("MEDOID",first["families"][0]["prototype_descriptor"]["type"])

    def test_all_residual_and_singleton_tendency_do_not_fake_families(self) -> None:
        m = matrix(["A","B","C"],{"A|B":"1","A|C":"1","B|C":"1"})
        result = medoid_star(m,FamilyMethodSpec("GREEDY_LEXICOGRAPHIC_MEDOID_STAR","CFG",radius="0.1",minimum_support=2))
        self.assertEqual([],result["families"]); self.assertEqual("NO_STABLE_FAMILY",result["evidence_status"])
        self.assertEqual(["A","B","C"],result["singleton_ids"])
        self.assertTrue(all(item["status"]=="RESIDUAL" for item in family_assignments(result)))

    def test_complete_and_average_linkage_preserve_small_cluster_residuals(self) -> None:
        m = matrix(["A","B","C","D"],{"A|B":"0.1","A|C":"0.2","A|D":"2","B|C":"0.2","B|D":"2","C|D":"2"})
        for linkage in ("complete","average"):
            result = hierarchical(m,FamilyMethodSpec(linkage.upper()+"_LINKAGE","CFG",radius="0.3",minimum_support=2,linkage=linkage))
            self.assertEqual(1,len(result["families"])); self.assertEqual(["D"],result["residual_ids"])
            self.assertEqual("EXEMPLAR_SET",result["families"][0]["prototype_descriptor"]["type"])

    def test_bounded_pam_can_leave_outlier_residual(self) -> None:
        m = matrix(["A","B","C","Z"],{"A|B":"0.1","A|C":"0.2","A|Z":"5","B|C":"0.1","B|Z":"5","C|Z":"5"})
        result = bounded_pam(m,FamilyMethodSpec("BOUNDED_PAM","CFG",k=1,minimum_support=2,max_assignment_distance="0.5",max_iterations=10))
        self.assertEqual(["Z"],result["residual_ids"]); self.assertEqual(1,len(result["families"]))

    def test_family_boundary_ties_use_lexicographic_medoid(self) -> None:
        m = matrix(["A","B","C"],{"A|B":"0.1","A|C":"0.1","B|C":"0.2"})
        result = medoid_star(m,FamilyMethodSpec("GREEDY_LEXICOGRAPHIC_MEDOID_STAR","CFG",radius="0.1",minimum_support=2))
        self.assertEqual("A",result["families"][0]["prototype_descriptor"]["record_id"])

    def test_full_assignment_is_never_a_success_target(self) -> None:
        m = matrix(["A","B"],{"A|B":"0.1"})
        result = medoid_star(m,FamilyMethodSpec("GREEDY_LEXICOGRAPHIC_MEDOID_STAR","CFG",radius="0.2"))
        self.assertFalse(result["full_assignment_target"])


if __name__ == "__main__":
    unittest.main()
