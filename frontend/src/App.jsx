import React from "react";

function App() {
  return (
    <div style={styles.container}>
      
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>Accord Dashboard</h1>
        <button style={styles.button}>+ Schedule Meeting</button>
      </div>

      {/* Cards */}
      <div style={styles.cardContainer}>
        <div style={styles.card}>
          <h3>Meetings</h3>
          <p>5 upcoming</p>
        </div>

        <div style={styles.card}>
          <h3>Email Insights</h3>
          <p>2 intents detected</p>
        </div>

        <div style={styles.card}>
          <h3>Productivity</h3>
          <p>78% efficiency</p>
        </div>
      </div>

      {/* Meeting Section */}
      <div style={styles.section}>
        <h2>Upcoming Meeting</h2>

        <div style={styles.meetingCard}>
          <div>
            <p style={styles.meetingTitle}>Client Discussion</p>
            <p style={styles.meetingSub}>Tomorrow • 3:00 PM</p>
          </div>

          <button style={styles.viewBtn}>View</button>
        </div>
      </div>

    </div>
  );
}

const styles = {
  container: {
    padding: "30px",
    maxWidth: "1000px",
    margin: "auto"
  },

  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "30px"
  },

  title: {
    fontSize: "28px",
    fontWeight: "600"
  },

  button: {
    backgroundColor: "#2563eb",
    color: "white",
    border: "none",
    padding: "10px 15px",
    borderRadius: "8px",
    cursor: "pointer"
  },

  cardContainer: {
    display: "flex",
    gap: "20px",
    marginBottom: "30px"
  },

  card: {
    flex: 1,
    background: "white",
    padding: "20px",
    borderRadius: "12px",
    boxShadow: "0 4px 15px rgba(0,0,0,0.1)",
    transition: "0.3s",
    cursor: "pointer"
  },

  section: {
    marginTop: "20px"
  },

  meetingCard: {
    background: "white",
    padding: "20px",
    borderRadius: "12px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    boxShadow: "0 4px 15px rgba(0,0,0,0.1)"
  },

  meetingTitle: {
    fontWeight: "600",
    margin: 0
  },

  meetingSub: {
    color: "#6b7280",
    marginTop: "5px"
  },

  viewBtn: {
    backgroundColor: "#111827",
    color: "white",
    border: "none",
    padding: "8px 12px",
    borderRadius: "6px",
    cursor: "pointer"
  }
};

export default App;