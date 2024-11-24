import simpy
from collections import deque
import random
from constant import *


class TicketMatrix:
    """Hệ thống vé theo dạng ma trận."""
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.matrix = [[0 for _ in range(cols)] for _ in range(rows)]  

    def display_matrix(self):
        """Hiển thị trạng thái vé."""
        print("\nTicket Matrix:")
        for row in self.matrix:
            print(" ".join(str(cell) for cell in row))

    def is_available(self, row, col):
        """Kiểm tra vé có sẵn không."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.matrix[row][col] == 0 
        return False

    def choose_ticket(self, row, col):
        """Chọn vé tại vị trí (row, col)."""
        if self.is_available(row, col):
            self.matrix[row][col] = 1  
            print(f"Ticket at ({row}, {col}) has been selected.")
            return True
        else:
            print(f"Ticket at ({row}, {col}) is not available!")
            return False

class Customer:
    def __init__(self, customer_id, arrival_time):
        self.customer_id = customer_id
        self.arrival_time = arrival_time
        self.queue_time = None  
        self.movie_ticket = None

    def select_ticket(self, ticket_matrix):
        for i in range(MAX_CHOICE_MOVIE):
            # row = random.randint(0, ticket_matrix.rows)
            # col = random.randint(0, ticket_matrix.cols)
            row = 1
            col = 1
            if ticket_matrix.is_available(row, col):
                ticket_matrix.choose_ticket(row, col)
                return row, col
        return None, None
    

class RoomQueue:
    def __init__(self, env):
        self.env = env
        self.queue = deque()
        self.waiting_area = reason_of_changing_film
        self.room_queue_success_list = []
        self.room_queue_failed_list = []

    def random_reason_and_count(self):
        choice = random.choice(list(self.waiting_area.keys()))
        if choice == "n":
            self.waiting_area["n"] += 1
            return False
        else:
            reason = random.choice(list(self.waiting_area["y"].keys()))
            self.waiting_area["y"][reason] += 1
            return True
        
    def come_into_theater(self):
        while True:
            if self.queue:
                customer = self.queue.popleft()  
                change_to_rollback = self.random_reason_and_count()
                if change_to_rollback == False:
                    yield self.env.timeout(WAITING_TO_COME_ROOM)  
                    self.room_queue_success_list.append(customer)
                    print(f"[{self.env.now:.2f}] Customer {customer.customer_id} success to go to movie theater")
                else:
                    yield self.env.timeout(WAITING_TO_COME_ROOM)  
                    self.room_queue_failed_list.append(customer)
                    print(f"[{self.env.now:.2f}] Customer {customer.customer_id} change decision")
            else:
                yield self.env.timeout(1)


class TicketQueue:
    def __init__(self, env, queue_id, room_queues):
        self.env = env
        self.queue_id = queue_id
        self.queue = deque()  
        self.success_ticket_list = []  
        self.failed_ticket_list = []  
        self.ticket_matrix = TicketMatrix(MATRIX_ROWS, MATRIX_COLS)  
        self.resource = simpy.Resource(env, capacity=1)  
        self.room_queues = room_queues

    def serve(self):
        while True:
            if self.queue:
                customer = self.queue.popleft()  
                print(f"[{self.env.now:.2f}] Ticket Queue {self.queue_id}: Serving Customer {customer.customer_id}.")
                self.ticket_matrix.display_matrix() 


                row, col = customer.select_ticket(self.ticket_matrix)
                if row is not None and col is not None:
                    print(f"[{self.env.now:.2f}] Customer {customer.customer_id} selected ticket at ({row}, {col}).")
                    yield self.env.timeout(TICKET_SERVICE_TIME)  
                    self.success_ticket_list.append(customer)
                    self.room_queues.queue.append(customer)
                    print(f"[{self.env.now:.2f}] Ticket Queue {self.queue_id}: Customer {customer.customer_id} served.")
                else:
                    self.failed_ticket_list.append(customer)
                    print(f"[{self.env.now:.2f}] Customer {customer.customer_id} failed to select a ticket.")
            else:
                yield self.env.timeout(1)  

class Entrance:
    def __init__(self, env, ticket_queues):
        self.env = env
        self.queue = deque() 
        self.ticket_queues = ticket_queues
        self.failure_list = []  

    def customer_arrival(self, customer):
        yield self.env.timeout(customer.arrival_time)
        print(f"[{self.env.now:.2f}] Customer {customer.customer_id} arrived at Entrance.")

        if len(self.queue) < ENTRANCE_CAPACITY:
            customer.queue_time = self.env.now  
            self.queue.append(customer)
            print(f"[{self.env.now:.2f}] Customer {customer.customer_id} entered the Entrance queue.")
        else:
            print(f"[{self.env.now:.2f}] Customer {customer.customer_id} could not enter Entrance (full).")

    def assign_to_ticket(self):
        while True:
            if self.queue:
                customer = self.queue[0] 
                wait_time = self.env.now - customer.queue_time
                if wait_time > MAX_WAIT_TIME:
                    self.queue.popleft()  
                    self.failure_list.append(customer)
                    print(f"[{self.env.now:.2f}] Customer {customer.customer_id} failed (waited too long at Entrance).")
                else:
                    selected_queue = min(self.ticket_queues, key=lambda q: len(q.queue))
                    if len(selected_queue.queue) < MAX_TICKET_QUEUE_CAPACITY:
                        self.queue.popleft()  
                        selected_queue.queue.append(customer)
                        print(f"[{self.env.now:.2f}] Customer {customer.customer_id} moved to Ticket Queue {selected_queue.queue_id}.")
                    else:
                        yield self.env.timeout(1)
            else:
                yield self.env.timeout(1)

class Simulation:
    def __init__(self):
        self.env = simpy.Environment()
        self.room_queues = RoomQueue(self.env)
        self.ticket_queues = [TicketQueue(self.env, i, self.room_queues) for i in range(NUM_TICKETS)]
        self.entrance = Entrance(self.env, self.ticket_queues)

    def setup(self):

        self.env.process(self.room_queues.come_into_theater())

        for ticket_queue in self.ticket_queues:
            self.env.process(ticket_queue.serve())

        self.env.process(self.entrance.assign_to_ticket())

        for i in range(NUM_CUSTOMERS):
            customer = Customer(i, i * ARRIVAL_INTERVAL)
            self.env.process(self.entrance.customer_arrival(customer))

    def run(self, duration=60):
        self.env.run(until=duration)
        self.print_results()

    def print_results(self):
        print("\n--- Simulation Results ---")
        total_success_ticket = sum(len(q.success_ticket_list) for q in self.ticket_queues)
        total_failures_ticket = len(self.entrance.failure_list)
        print(f"Total customers served in ticket area: {total_success_ticket}")
        print(f"Total customers failed in ticket area: {total_failures_ticket}")
        for i, ticket_queue in enumerate(self.ticket_queues):
            print(f"Ticket Queue {i}: {len(ticket_queue.success_ticket_list)} customers served in area.")
            # print(f"Ticket Queue {i}: {len(ticket_queue.failed_ticket_list)} customers served.")
        
        total_success_waiting = len(self.room_queues.room_queue_success_list)
        total_failures_waiting = len(self.room_queues.room_queue_failed_list)

        print(f"Total: {total_success_waiting} customers come into area.")
        print(f"Total: {total_failures_waiting} customers do not come into area.")

# Chạy mô phỏng
simulation = Simulation()
simulation.setup()
simulation.run()


# Lấy ra được số người thành công được tiến hành qua Ticket Processing Area ( customer_success_entering_ticket_processing_area )
# Lấy ra được số người out hàng chờ trước khi được tiến hành qua Ticket Processing Area( customer_exit_from_processing )

# Lấy ra được số người mua vé thành công và được tiếp tục qua khu vực waiting area ( ticket_buy_success )
# Lấy ra được số người out hàng chờ trước khi đến lượt mua vé ( customer_exit_before_bought_ticket )
# Lấy ra được số người đặt vé không thành công do không có chỗ ngồi phù hợp ( customer_exit_while_bought_ticket )
# Tổng số người hiện tại có trong khu vực Ticket Processing Area(total_customers_in_ticket_area)


# Lấy ra được số người thành công vào phòng xem phim ( customer_success_enter_room )
# Lấy ra được số người out waiting room khi có mong muốn mua lại vé phim khác ( hoặc đổi vé )( customer_exit_before_enter_room )
# Hệ thống sẽ tiến hành ghi lại số lượng của mỗi lí do rollback để thống kê ( ví dụ số lượng lí do "thay đổi phim" , số lượng lí do "thay đổi chỗ ngồi")