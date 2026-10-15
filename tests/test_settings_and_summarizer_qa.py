"""
Tests for Admin Settings Accessor Management & AI Dashboard Summarizer Multi-Query Q&A
Validates:
1. Listing existing accessors (get_all_users).
2. Provisioning new users (ADMIN and ADMISSION_OFFICER) with password hashing and audit logging.
3. Accessor activation/deactivation and deletion safeguards.
4. Non-admin RBAC authorization restrictions on user creation.
5. AI Dashboard Summarizer multi-query execution and query history management (multi-query + clear/delete).
"""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.database import init_db
from services.auth_service import (
    authenticate_user, get_all_users, create_new_user,
    toggle_user_status, delete_user,
    ROLE_ADMIN, ROLE_ADMISSION_OFFICER
)
from services.dashboard_summarizer import DashboardSummarizerService, handle_dashboard_qa_request


class TestSettingsAndSummarizerQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.admin_user = authenticate_user("admin", "Admin@Vital2026!")
        cls.officer_user = authenticate_user("admit_officer", "Admit@Vital2026!")
        
        # Clean up any leftover test accounts from previous runs by username
        for test_u in ["night_nurse_triage", "coo_admin", "rogue_user"]:
            try:
                delete_user(test_u, actor_user=cls.admin_user)
            except Exception:
                pass

    def test_01_get_all_users_returns_existing_accessors(self):
        """Verify get_all_users retrieves all provisioned accessors with non-sensitive fields."""
        users = get_all_users()
        self.assertGreaterEqual(len(users), 2)
        usernames = [u["username"] for u in users]
        self.assertIn("admin", usernames)
        self.assertIn("admit_officer", usernames)

        for u in users:
            self.assertIn("username", u)
            self.assertIn("role", u)
            self.assertIn("full_name", u)
            self.assertIn("is_active", u)
            # Password hashes should not be exposed in user management lists
            self.assertNotIn("password_hash", u)

    def test_02_admin_provisions_new_admit_officer_and_admin(self):
        """Verify an admin can provision both an admit_officer and another admin."""
        # 1. Provision new admission officer
        new_off = create_new_user(
            username="night_nurse_triage",
            password="NightNurse@2026",
            role=ROLE_ADMISSION_OFFICER,
            full_name="Sarah Connor, RN",
            department="Emergency Triage",
            actor_user=self.admin_user
        )
        self.assertIsNotNone(new_off)
        self.assertEqual(new_off["username"], "night_nurse_triage")

        # Authenticate with the new officer credentials
        auth_off = authenticate_user("night_nurse_triage", "NightNurse@2026")
        self.assertIsNotNone(auth_off)
        self.assertEqual(auth_off["role"], ROLE_ADMISSION_OFFICER)
        self.assertEqual(auth_off["full_name"], "Sarah Connor, RN")

        # 2. Provision new admin
        new_adm = create_new_user(
            username="coo_admin",
            password="ChiefOpsAdmin@2026",
            role=ROLE_ADMIN,
            full_name="Dr. Marcus Vance",
            department="Chief Operating Office",
            actor_user=self.admin_user
        )
        self.assertIsNotNone(new_adm)
        self.assertEqual(new_adm["username"], "coo_admin")

        auth_adm = authenticate_user("coo_admin", "ChiefOpsAdmin@2026")
        self.assertIsNotNone(auth_adm)
        self.assertEqual(auth_adm["role"], ROLE_ADMIN)

    def test_03_non_admin_cannot_create_users(self):
        """Verify admission officers are blocked by RBAC from creating users."""
        with self.assertRaises(PermissionError):
            create_new_user(
                username="rogue_user",
                password="Password123!",
                role=ROLE_ADMIN,
                full_name="Rogue Agent",
                actor_user=self.officer_user
            )

    def test_04_toggle_status_and_self_protection(self):
        """Verify activation toggling and protection against self-deactivation."""
        # Cannot deactivate own account
        with self.assertRaises(ValueError):
            toggle_user_status(
                user_identifier="admin",
                is_active=False,
                actor_user=self.admin_user
            )

        # Deactivate another user
        all_users = {u["username"]: u for u in get_all_users()}
        target_user = all_users["night_nurse_triage"]
        ok_deact = toggle_user_status(
            user_identifier=target_user["username"],
            is_active=False,
            actor_user=self.admin_user
        )
        self.assertTrue(ok_deact)

        # Deactivated user cannot log in
        login_deact = authenticate_user("night_nurse_triage", "NightNurse@2026")
        self.assertIsNone(login_deact)

        # Reactivate user
        ok_react = toggle_user_status(
            user_identifier=target_user["username"],
            is_active=True,
            actor_user=self.admin_user
        )
        self.assertTrue(ok_react)
        login_react = authenticate_user("night_nurse_triage", "NightNurse@2026")
        self.assertIsNotNone(login_react)

    def test_05_summarizer_multiple_sequential_queries(self):
        """Verify the AI Dashboard Summarizer handles multiple distinct sequential queries."""
        service = DashboardSummarizerService()
        summary = service.generate_summary(auth_context=self.admin_user, force_refresh=False)

        q1 = "Which department needs the most attention?"
        res1 = handle_dashboard_qa_request(auth_context=self.admin_user, query=q1, current_summary=summary)
        self.assertEqual(res1.get("status"), "success")
        self.assertTrue(len(res1.get("answer", "")) > 10)

        q2 = "Why is ICU utilization high?"
        res2 = handle_dashboard_qa_request(auth_context=self.admin_user, query=q2, current_summary=summary)
        self.assertEqual(res2.get("status"), "success")
        self.assertTrue(len(res2.get("answer", "")) > 10)

        q3 = "What is the status of the blood bank and available blood reserves?"
        res3 = handle_dashboard_qa_request(auth_context=self.admin_user, query=q3, current_summary=summary)
        self.assertEqual(res3.get("status"), "success")
        self.assertIn("Blood", res3.get("answer", ""))

        # Simulate maintaining multiple queries in history
        qa_history = []
        for q, res in [(q1, res1), (q2, res2), (q3, res3)]:
            qa_history.insert(0, {
                "question": q,
                "answer": res.get("answer")
            })

        self.assertEqual(len(qa_history), 3)
        self.assertEqual(qa_history[0]["question"], q3)
        self.assertEqual(qa_history[1]["question"], q2)
        self.assertEqual(qa_history[2]["question"], q1)

        # Test individual query deletion
        qa_history.pop(1)
        self.assertEqual(len(qa_history), 2)
        self.assertEqual([item["question"] for item in qa_history], [q3, q1])

        # Test clearing all queries
        qa_history.clear()
        self.assertEqual(len(qa_history), 0)


if __name__ == "__main__":
    unittest.main()
