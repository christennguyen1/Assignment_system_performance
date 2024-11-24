from datetime import datetime



def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def calculate_hours(time1, time2):
    # Chuyển đổi các chuỗi thời gian thành datetime object
    time1 = datetime.strptime(time1, "%Y-%m-%d %H:%M:%S")
    time2 = datetime.strptime(time2, "%Y-%m-%d %H:%M:%S")
    
    # Tính toán sự khác biệt giữa hai thời gian
    delta = time2 - time1
    
    # Chuyển sự khác biệt thành giờ
    hours = delta.total_seconds()  # total_seconds() trả về tổng số giây
    return hours