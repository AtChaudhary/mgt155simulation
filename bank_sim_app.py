import streamlit as st
import simpy
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import time

# Simulation class
class BankSystem:
    def __init__(self, env, sim_time, num_cashiers, arrival_rate,
                 atm_service_time, cashier_service_time, atm_prob):
        self.env = env
        self.sim_time = sim_time
        self.cashiers = simpy.Resource(env, capacity=num_cashiers)
        self.atm = simpy.Resource(env, capacity=1)

        self.arrival_rate = arrival_rate
        self.atm_service_time = atm_service_time
        self.cashier_service_time = cashier_service_time
        self.atm_prob = atm_prob

        self.flow_time = []
        self.inv_time = []
        self.inv_queue = []

        self.atm_busy_time = 0.0
        self.cashier_busy_time = 0.0
        self.last_recorded_time = 0.0

        env.process(self.generate_customers())

    def generate_customers(self):
        while True:
            yield self.env.timeout(np.random.exponential(1.0 / self.arrival_rate))
            self.env.process(self.customer_process())

    def customer_process(self):
        arrival = self.env.now

        if np.random.uniform() < self.atm_prob:
            with self.atm.request() as req:
                yield req
                start = self.env.now
                duration = self.sample_triangular(*self.atm_service_time)
                yield self.env.timeout(duration)
                self.atm_busy_time += duration
        with self.cashiers.request() as req:
            yield req
            start = self.env.now
            duration = self.sample_triangular(*self.cashier_service_time)
            yield self.env.timeout(duration)
            self.cashier_busy_time += duration

        self.flow_time.append(self.env.now - arrival)

        # Record queue length over time (sample every 1 minute)
        if self.env.now - self.last_recorded_time >= 1:
            self.inv_time.append(self.env.now)
            self.inv_queue.append([
                len(self.atm.queue),
                len(self.cashiers.queue)
            ])
            self.last_recorded_time = self.env.now

    def sample_triangular(self, low, mode, high):
        return np.random.triangular(low, mode, high)

# --- Streamlit UI ---

st.title("🏦 Bank Queue Simulation")

st.sidebar.header("Simulation Parameters")
sim_time = st.sidebar.slider("Simulation Time (minutes)", 100,1000000, 50000)
arrival_rate = st.sidebar.slider("Customer Arrival Rate (per min)", 0.10, 5, 0.75)
num_cashiers = st.sidebar.slider("Number of Cashiers", 1, 25, 5)
atm_prob = st.sidebar.slider("Probability Customer Goes to ATM First", 0.0, 1.0, 0.5)

st.sidebar.markdown("### ATM Service Time (Triangular)")
atm_low = st.sidebar.number_input("ATM Min Time", 0.5, 10.0, 1.0)
atm_mode = st.sidebar.number_input("ATM Mode Time", 0.5, 10.0, 2.0)
atm_high = st.sidebar.number_input("ATM Max Time", 0.5, 10.0, 3.0)

st.sidebar.markdown("### Cashier Service Time (Triangular)")
cashier_low = st.sidebar.number_input("Cashier Min Time", 1.0, 20.0, 2.0)
cashier_mode = st.sidebar.number_input("Cashier Mode Time", 1.0, 20.0, 4.0)
cashier_high = st.sidebar.number_input("Cashier Max Time", 1.0, 20.0, 6.0)

if st.button("Run Simulation"):
    # Run simulation
    env = simpy.Environment()
    system = BankSystem(
        env, sim_time, num_cashiers, arrival_rate,
        (atm_low, atm_mode, atm_high),
        (cashier_low, cashier_mode, cashier_high),
        atm_prob
    )
    env.run(until=sim_time)

    # KPIs
    st.header("📊 Simulation Results")
    total_customers = len(system.flow_time)
    avg_time = np.mean(system.flow_time)
    st.metric("Total Customers Served", total_customers)
    st.metric("Average Time in Bank", f"{avg_time:.2f} minutes")
    st.metric("ATM Utilization", f"{system.atm_busy_time / sim_time:.2%}")
    st.metric("Cashier Utilization", f"{system.cashier_busy_time / (sim_time * num_cashiers):.2%}")

    # Histogram of time in bank
    st.subheader("⏱ Distribution of Time in Bank")
    fig, ax = plt.subplots()
    ax.hist(system.flow_time, bins=30, color="skyblue", edgecolor="black")
    ax.set_xlabel("Time in Bank (minutes)")
    ax.set_ylabel("Number of Customers")
    st.pyplot(fig)

    # Queue length chart
    st.subheader("📉 Queue Lengths Over Time")
    df_q = pd.DataFrame(system.inv_queue, columns=["ATM Queue", "Cashier Queue"])
    df_q["Time"] = system.inv_time
    st.line_chart(df_q.set_index("Time"))

    # Animation block
    st.subheader("🔄 Simulation Playback")
    placeholder = st.empty()
    for t, (atm_q, cashier_q) in zip(system.inv_time, system.inv_queue):
        with placeholder.container():
            st.markdown(f"**Time: {t:.1f} min**")
            col1, col2 = st.columns(2)
            col1.metric("ATM Queue", atm_q)
            col2.metric("Cashier Queue", cashier_q)
        time.sleep(0.05)
    st.success("Simulation completed successfully!")    
    
