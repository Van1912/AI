# Core/neighborhood.py
import random
from typing import List, Callable


# ============================================================
# Neighborhood operators for priority list (List[str])
# ============================================================

def nb_swap(p: List[str]) -> List[str]:
    """
    Swap:
    - Hoán đổi vị trí của 2 công việc bất kỳ
    - Khám phá không gian lân cận cục bộ
    """
    if len(p) < 2:
        return p[:]

    i, j = random.sample(range(len(p)), 2)
    q = p[:]
    q[i], q[j] = q[j], q[i]
    return q


def nb_insert(p: List[str]) -> List[str]:
    """
    Insert (Shift):
    - Lấy 1 công việc ra khỏi vị trí i
    - Chèn vào vị trí j
    - Phù hợp để sửa các thứ tự 'gần đúng'
    """
    if len(p) < 2:
        return p[:]

    i, j = random.sample(range(len(p)), 2)
    q = p[:]

    x = q.pop(i)

    # điều chỉnh chỉ số khi pop
    if i < j:
        j -= 1

    q.insert(j, x)
    return q


def nb_reverse_segment(p: List[str]) -> List[str]:
    """
    Reverse segment (2-opt):
    - Đảo ngược một đoạn liên tiếp [i, j]
    - Giúp thoát local optimum tốt hơn
    """
    if len(p) < 3:   # Cần ít nhất 3 task để đảo đoạn có ý nghĩa 
        return p[:]

    i, j = sorted(random.sample(range(len(p)), 2))  # CHỌN 2 đầu i < j 
    q = p[:]
    q[i:j+1] = list(reversed(q[i:j+1]))   # đảo ngược đoạn i,j 
    return q


# ============================================================
# Export list of neighborhood operators
# ============================================================

NEIGHBORS: List[Callable[[List[str]], List[str]]] = [
    nb_swap,
    nb_insert,
    nb_reverse_segment,
]
