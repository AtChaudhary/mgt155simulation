import streamlit as st
import numpy as np
import simpy
import matplotlib.pyplot as plt

class ServerSystem:
    def __init__(self, sim_time, num_cashiers, arrival_rate, max_service_time):
        self.sim_time = sim_time
        self.num_cashiers = num_cashiers
        self.arrival_rate = arrival_rate
        self.max_service_time = max_service_time

        self.env = simpy.Environment()
        self.atm = simpy.Resource(self.env, capacity=1)
        self.cashiers = simpy.Resource(self.env, capacity=self.num_cashiers)

        self.flow_time = []
        self.wait_time = []
        self.finished_customers = 0
        self.inv_time = []
        self.inv_queue = []
        self.inv_service = []
        self.inv_system = []

    def monitor(self):
        while True:
            current_time = self.env.now
            atm_queue_len = len(self.atm.queue)
            cashier_queue_len = len(self.cashiers.queue)
            self.inv_time.append(current_time)
            self.inv_queue.append((atm_queue_len, cashier_queue_len))
            self.inv_service.append((len(self.atm.users), len(self.cashiers.users)))
            self.inv_system.append(atm_queue_len + cashier_queue_len + len(self.atm.users) + len(self.cashiers.users))
            yield self.env.timeout(1)

    def use_cashier(self, arrival_time):
        with self.cashiers.request() as request:
            yield request
            self.wait_time.append(self.env.now - arrival_time)
            yield self.env.timeout(np.random.triangular(3, 5, self.max_service_time))
            self.finished_customers += 1
            self.flow_time.append(self.env.now - arrival_time)

    def customer(self, arrival_time):
        if np.random.uniform() < 0.5:
            with self.atm.request() as request:
                yield request
                self.wait_time.append(self.env.now - arrival_time)
                yield self.env.timeout(np.random.triangular(1, 2, 4))
            if np.random.uniform() < 0.3:
                yield self.env.process(self.use_cashier(arrival_time))
            else:
                self.finished_customers += 1
                self.flow_time.append(self.env.now - arrival_time)
        else:
            yield self.env.process(self.use_cashier(arrival_time))

    def gen_arrivals(self):
        while True:
            yield self.env.timeout(np.random.exponential(1 / self.arrival_rate))
            self.env.process(self.customer(self.env.now))

    def simulate(self):
        self.env.process(self.monitor())
        self.env.process(self.gen_arrivals())
        self.env.run(until=self.sim_time)

# Streamlit interface
st.title("🏦 Bank Process Flow Simulation")
st.write("Adjust the parameters and rerun the simulation.")

sim_time = st.slider("Simulation Time (minutes)", 1000, 10000000, 50000, step=500)
arrival_rate = st.slider("Arrival Rate (customers/min)", 0.1, 5.0, 0.75, step=0.05)
num_cashiers = st.slider("Number of Cashiers", 1, 20, 5)
max_service_time = st.slider("Cashier Max Service Time (minutes)", 10, 30, 20)

if st.button("Run Simulation"):
    system = ServerSystem(sim_time, num_cashiers, arrival_rate, max_service_time)
    system.simulate()

    # Metrics
    mean_flow_time = np.mean(system.flow_time)
    mean_wait_time = np.mean(system.wait_time)
    mean_atm_q = np.mean([q[0] for q in system.inv_queue])
    mean_cashier_q = np.mean([q[1] for q in system.inv_queue])
    cashier_util = np.mean([s[1] for s in system.inv_service]) / num_cashiers

    st.subheader("📊 KPIs")
    st.write(f"**Avg Time in Bank:** {mean_flow_time:.2f} mins")
    st.write(f"**Avg Wait Time:** {mean_wait_time:.2f} mins")
    st.write(f"**Cashier Utilization:** {cashier_util * 100:.2f}%")
    st.write(f"**Mean Queue Length - ATM:** {mean_atm_q:.2f}")
    st.write(f"**Mean Queue Length - Cashiers:** {mean_cashier_q:.2f}")
    st.write(f"**Total Customers Served:** {system.finished_customers}")

    st.subheader("⏱ Distribution of Time in System")
    fig, ax = plt.subplots()
    ax.hist(system.flow_time, bins=30, edgecolor='black')
    ax.set_xlabel("Time in System (minutes)")
    ax.set_ylabel("Number of Customers")
    ax.set_title("Distribution of Time in Bank")
    st.pyplot(fig)
