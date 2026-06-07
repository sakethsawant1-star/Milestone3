"use client";

import { useState } from "react";
import styles from "./page.module.css";

export default function Home() {
  const [reviewCount, setReviewCount] = useState(50);
  const [skipScrape, setSkipScrape] = useState(false);
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const [runUrl, setRunUrl] = useState("");

  const handleTrigger = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setMessage("Triggering Google Cloud / GitHub Actions pipeline...");
    setRunUrl("");

    try {
      const response = await fetch("/api/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reviewCount, skipScrape }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to trigger analysis.");
      }

      setStatus("success");
      setMessage("Pipeline successfully triggered! Analysis is running in the background.");
      if (data.run_url) {
        setRunUrl(data.run_url);
      }
    } catch (error: any) {
      setStatus("error");
      setMessage(error.message);
    }
  };

  return (
    <main className={styles.main}>
      <div className={styles.header}>
        <h1 className={styles.title}>Groww Review Analyst</h1>
        <p className={styles.subtitle}>Automated App Store Intelligence</p>
      </div>

      <form className={styles.card} onSubmit={handleTrigger}>
        <div className={styles.formGroup}>
          <label className={styles.label} htmlFor="reviewCount">
            Reviews to analyze (max 100)
          </label>
          <input
            id="reviewCount"
            className={styles.input}
            type="number"
            min="10"
            max="100"
            value={reviewCount}
            onChange={(e) => setReviewCount(Number(e.target.value))}
            required
          />
          <div className={styles.checkboxGroup}>
            <input
              id="skipScrape"
              className={styles.checkbox}
              type="checkbox"
              checked={skipScrape}
              onChange={(e) => setSkipScrape(e.target.checked)}
            />
            <label htmlFor="skipScrape" style={{ color: "var(--text-secondary)" }}>
              Skip scraping (use cached data)
            </label>
          </div>
        </div>

        <button 
          type="submit" 
          className={styles.button}
          disabled={status === "loading"}
        >
          {status === "loading" ? (
            <>
              <div className={styles.spinner} />
              Triggering...
            </>
          ) : (
            "Run Analysis Now"
          )}
        </button>

        {status !== "idle" && status !== "loading" && (
          <div className={`${styles.statusCard} ${styles[status]}`}>
            <span className={styles.statusTitle}>
              {status === "success" ? "Success" : "Error"}
            </span>
            <span className={styles.statusMessage}>{message}</span>
            {status === "success" && runUrl && (
              <a 
                href={runUrl} 
                target="_blank" 
                rel="noopener noreferrer"
                className={styles.link}
              >
                View Pipeline Progress &rarr;
              </a>
            )}
          </div>
        )}
      </form>
    </main>
  );
}
