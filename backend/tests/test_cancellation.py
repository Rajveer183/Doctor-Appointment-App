async def test_patient_cancel_within_window_is_rejected(client_with_seed):
    client, ids = client_with_seed

    booked = await client.post(
        "/api/appointments", json={"slot_id": ids["near_slot_id"], "patient_id": ids["patient_a"], "reason": "x"}
    )
    assert booked.status_code == 201
    appointment_id = booked.json()["id"]

    cancel = await client.patch(f"/api/appointments/{appointment_id}/cancel")
    assert cancel.status_code == 409
    assert "cancel" in cancel.json()["detail"].lower()

    # Rejected cancel must not have changed anything.
    appt = (await client.get(f"/api/appointments/{appointment_id}")).json()
    assert appt["status"] == "confirmed"
    assert appt["slot"]["status"] == "booked"


async def test_patient_cancel_outside_window_succeeds(client_with_seed):
    client, ids = client_with_seed

    booked = await client.post(
        "/api/appointments", json={"slot_id": ids["slot_id"], "patient_id": ids["patient_a"], "reason": "x"}
    )
    assert booked.status_code == 201
    appointment_id = booked.json()["id"]

    cancel = await client.patch(f"/api/appointments/{appointment_id}/cancel")
    assert cancel.status_code == 200
    body = cancel.json()
    assert body["status"] == "cancelled"
    assert body["cancelled_at"] is not None
    assert body["slot"]["status"] == "open"


async def test_admin_cancel_bypasses_window(client_with_seed):
    client, ids = client_with_seed

    booked = await client.post(
        "/api/appointments", json={"slot_id": ids["near_slot_id"], "patient_id": ids["patient_a"], "reason": "x"}
    )
    assert booked.status_code == 201
    appointment_id = booked.json()["id"]

    # Same appointment that the patient-facing cancel test rejects — the admin/doctor
    # path (PATCH .../status) enforces no window.
    result = await client.patch(f"/api/appointments/{appointment_id}/status", json={"status": "cancelled"})
    assert result.status_code == 200
    assert result.json()["status"] == "cancelled"


async def test_invalid_status_transition_rejected(client_with_seed):
    client, ids = client_with_seed

    booked = await client.post(
        "/api/appointments", json={"slot_id": ids["slot_id"], "patient_id": ids["patient_a"], "reason": "x"}
    )
    appointment_id = booked.json()["id"]

    cancelled = await client.patch(f"/api/appointments/{appointment_id}/status", json={"status": "cancelled"})
    assert cancelled.status_code == 200

    # A cancelled appointment can't then be completed.
    invalid = await client.patch(f"/api/appointments/{appointment_id}/status", json={"status": "completed"})
    assert invalid.status_code == 422
