import time, requests

API = "http://localhost:8000"

ARTICLES = [
    "Tata Motors reported a 12% increase in quarterly revenue, reaching Rs 18,000 crore.",
    "Infosys announced a share buyback of Rs 9,000 crore, according to a regulatory filing.",
    "Reliance Industries posted a net profit of Rs 19,641 crore for Q3 FY24.",
    "HDFC Bank reported a 33% rise in net profit, driven by strong loan growth.",
    "Wipro guided for a 1-2% revenue decline next quarter.",
    "TCS won a $500 million multi-year deal with a European retailer.",
    "Adani Ports completed the acquisition of a 50% stake in a Sri Lankan terminal.",
    "Bharti Airtel added 3.2 million subscribers in December.",
    "ICICI Bank raised Rs 15,000 crore through a QIP.",
    "Maruti Suzuki recalled 16,000 units of the Baleno over a fuel-pump issue.",
    "Sun Pharma received US FDA approval for a generic oncology drug.",
    "Larsen & Toubro secured an order worth Rs 5,000 crore from a Middle East client.",
    "State Bank of India reported a 62% jump in quarterly net profit.",
    "Asian Paints saw a 3% volume growth in the decorative segment.",
    "Bajaj Auto launched a new electric scooter at Rs 1.2 lakh.",
    "NTPC commissioned a 300 MW solar plant in Rajasthan.",
    "ONGC discovered a new oil field in the Krishna-Godavari basin.",
    "Cipla acquired a US-based specialty pharma company for $250 million.",
    "JSW Steel raised steel prices by Rs 1,500 per tonne.",
    "Mahindra & Mahindra reported a 20% increase in SUV sales.",
]

def main():
    t0 = time.time()
    task_ids = []
    for text in ARTICLES:
        r = requests.post(f"{API}/articles/submit",
                          json={"text": text, "risk_level": "normal"})
        r.raise_for_status()
        task_ids.append(r.json()["task_id"])
    submit_s = time.time() - t0
    print(f"Submitted {len(task_ids)} articles in {submit_s:.2f}s")

    pending = set(task_ids)
    t1 = time.time()
    while pending and time.time() - t1 < 300:
        for tid in list(pending):
            state = requests.get(f"{API}/tasks/{tid}").json()["state"]
            if state in ("SUCCESS", "FAILURE"):
                pending.remove(tid)
        time.sleep(2)
    elapsed = time.time() - t1
    done = len(task_ids) - len(pending)
    print(f"Processed {done}/{len(task_ids)} in {elapsed:.1f}s "
          f"({done / elapsed * 60:.1f} articles/min)")
    if pending:
        print("Still pending:", pending)

if __name__ == "__main__":
    main()

