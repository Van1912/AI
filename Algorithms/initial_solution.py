# Algorithms/initial_solution.py

# Sinh nghiệm khởi tạo cho thuật toán tối ưu 
# Giải mã priority list thành schedule thực tế 
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

from Model.models import Task, Resource, Schedule, Assignment


# ============================================================
# Priority list builders (nghiệm khởi tạo)
# ============================================================

def priority_list_edd(tasks: List[Task]) -> List[str]:
    """
    EDD (Earliest Due Date):
    Công việc có deadline sớm hơn sẽ được ưu tiên trước.
    """
    return [t.id for t in sorted(tasks, key=lambda x: x.due_date)]


def priority_list_spt(tasks: List[Task]) -> List[str]:
    """
    SPT (Shortest Processing Time):
    Công việc có thời gian xử lý ngắn hơn được ưu tiên trước.
    """
    return [t.id for t in sorted(tasks, key=lambda x: x.duration_min)]


def priority_list_priority(tasks: List[Task]) -> List[str]:
    """
    Ưu tiên theo độ ưu tiên (priority) giảm dần,
    nếu bằng nhau thì xét deadline sớm hơn.
    """
    return [t.id for t in sorted(tasks, key=lambda x: (-x.priority, x.due_date))]


# ============================================================
# Decoder: priority list -> Schedule
# ============================================================

def decode_priority_list(
    priority: List[str],
    tasks_map: Dict[str, Task],
    resources: List[Resource],
) -> Tuple[Schedule, List[str]]:
    """
    Chuyển một priority list (thứ tự ưu tiên task)
    thành một Schedule (lịch phân công thực tế).

    Nguyên tắc mô phỏng doanh nghiệp:
    - Mỗi task được giao cho 1 resource phù hợp
    - Không chồng chéo thời gian trên cùng resource
    - Tôn trọng:
        + release_time
        + quan hệ trước–sau (predecessors)
    - Chọn resource sao cho task hoàn thành sớm nhất
    """
    notes: List[str] = []  # log cảnh báo 
    schedule = Schedule()  # lịch rỗng ban đầu 

    if not priority or not resources:   # kiểm tra có task và resource ko
        notes.append("Decoder: empty priority or resources.")
        return schedule, notes

    # --------------------------------------------------------
    # Thời điểm sớm nhất trong toàn bộ task (mốc bắt đầu chung)
    # --------------------------------------------------------
    global_start: datetime = min(
        tasks_map[tid].release_time
        for tid in priority
        if tid in tasks_map
    )
    # Lấy realease_time sớm nhất trong tất cả task

    # --------------------------------------------------------
    # Thời điểm resource sẵn sàng (resource -> datetime)
    # --------------------------------------------------------
    res_ready: Dict[str, Optional[datetime]] = {
        r.id: global_start for r in resources
    }

    # --------------------------------------------------------
    # Theo dõi thời điểm kết thúc của các task đã schedule
    # --------------------------------------------------------
    done_end: Dict[str, Optional[datetime]] = {}

    # Danh sách task chưa schedule
    remaining: List[str] = [tid for tid in priority if tid in tasks_map]

    guard = 0  # tránh vòng lặp vô hạn

    while remaining and guard < 10_000:
        guard += 1
        progressed = False # kiểm tra có schedule được tấk nào không 

        # Duyệt theo thứ tự ưu tiên hiện tại
        for tid in remaining[:]:
            t = tasks_map[tid]

            # --------------------------------------------
            # Kiểm tra predecessors đã hoàn thành chưa
            # --------------------------------------------
            preds_ok = True
            preds_end_max: datetime = global_start

            for p in t.predecessors:
                if p not in done_end:
                    preds_ok = False
                    break
                if done_end[p] and done_end[p] > preds_end_max:  # lấy thời điểm kết thúc muộn nhất của các predecessor 
                    preds_end_max = done_end[p]

            if not preds_ok:
                continue

            # --------------------------------------------
            # Chọn resource tốt nhất (hoàn thành sớm nhất)
            # --------------------------------------------
            best_r: Optional[Resource] = None
            best_start: Optional[datetime] = None
            best_end: Optional[datetime] = None

            for r in resources:
                # Kiểm tra loại resource (không phù hợp)
                if (
                    t.required_type != "ANY"
                    and r.rtype != "ANY"
                    and t.required_type != r.rtype
                ):
                    continue
                # Tính thời gian chạy(task chỉ được chạy khi: resource rảnh, task được release, predecessor xong)
                start = max(res_ready[r.id], t.release_time, preds_end_max)
                end = start + timedelta(minutes=t.duration_min)

                if best_end is None or end < best_end:
                    best_r = r
                    best_start = start
                    best_end = end

            # --------------------------------------------
            # Không tìm được resource phù hợp
            # --------------------------------------------
            if best_r is None:
                notes.append(
                    f"Decoder: Task {tid} has no compatible resource "
                    f"(required_type={t.required_type})."
                )
                remaining.remove(tid)
                progressed = True
                continue

            # --------------------------------------------
            # Tạo assignment hợp lệ
            # --------------------------------------------
            assignment = Assignment(
                task_id=tid,
                resource_id=best_r.id,
                start=best_start,
                end=best_end,
            )
            schedule.add(assignment)

            # Cập nhật trạng thái
            res_ready[best_r.id] = best_end
            done_end[tid] = best_end

            remaining.remove(tid)
            progressed = True

        # ----------------------------------------------------
        # Không schedule được task nào → phá bế tắc
        # ----------------------------------------------------
        if not progressed:
            tid = remaining.pop(0)  # lấy task đầu 
            t = tasks_map[tid]

            candidates = [
                r for r in resources
                if (
                    t.required_type == "ANY"
                    or r.rtype == "ANY"
                    or t.required_type == r.rtype
                )
            ]

            if not candidates:
                notes.append(f"Decoder stuck: no resource for {tid}. Dropped.")
                continue

            r = candidates[0]
            start = max(res_ready[r.id], t.release_time)
            end = start + timedelta(minutes=t.duration_min)

            schedule.add(Assignment(tid, r.id, start, end))
            res_ready[r.id] = end
            done_end[tid] = end

            notes.append(
                f"Decoder stuck: forced scheduling {tid} "
                f"(may violate precedence)."
            )

    if guard >= 10_000:
        notes.append("Decoder: guard reached, possible infinite loop.")

    return schedule, notes
