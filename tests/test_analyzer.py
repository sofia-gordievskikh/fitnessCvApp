"""Unit-тесты BodyAnalyzer, angles и подсчёта повторений."""
from ml.angles import angle_3pt, joint_angles
from ml.inference import BodyAnalyzer
from ml.reps import RepCounter


def test_angle_3pt_right_angle():
    assert angle_3pt((0, 1), (0, 0), (1, 0)) == 90.0


def test_angle_3pt_straight():
    assert angle_3pt((-1, 0), (0, 0), (1, 0)) == 180.0


def test_joint_angles_partial_keypoints():
    # без ankle угол колена не считается, но упасть не должно
    angles = joint_angles({"shoulder": (0, 0), "hip": (0, 1)})
    assert "knee" not in angles
    assert "back" in angles


def test_analyzer_basic_fields(squat_image):
    a = BodyAnalyzer()
    r = a.analyze_frame(squat_image, "squat.jpg", exercise="squat")
    assert r.exercise_type == "squat"
    assert 0.0 <= r.form_score <= 1.0
    assert len(r.parts) >= 4
    assert "knee" in r.joint_angles


def test_analyzer_deterministic(squat_image):
    a = BodyAnalyzer()
    r1 = a.analyze_bytes(squat_image, "squat.jpg", exercise="squat")
    r2 = a.analyze_bytes(squat_image, "squat.jpg", exercise="squat")
    assert r1 == r2


def test_depth_increases_at_bottom(squat_frames):
    a = BodyAnalyzer()
    depths = [a.analyze_frame(f, f"f{i}", exercise="squat").depth for i, f in enumerate(squat_frames)]
    # низ приседа в середине последовательности глубже, чем старт
    assert max(depths) > depths[0] + 0.3


def test_rep_counter_counts_one_squat(squat_frames):
    a = BodyAnalyzer()
    rc = RepCounter.for_exercise("squat")
    for i, f in enumerate(squat_frames):
        rc.update(a.analyze_frame(f, f"f{i}", exercise="squat").joint_angles.get("knee"))
    assert rc.count == 1


def test_rep_counter_hysteresis_no_double_count():
    rc = RepCounter.for_exercise("squat")
    # дрожание около верхнего порога не должно накручивать повторения
    for angle in [170, 162, 170, 161, 170]:
        rc.update(angle)
    assert rc.count == 0


def test_bad_image_returns_empty():
    a = BodyAnalyzer()
    r = a.analyze_bytes(b"not-an-image", "broken.jpg")
    assert r["parts"] == []
    assert "decode failed" in r["notes"][0]
