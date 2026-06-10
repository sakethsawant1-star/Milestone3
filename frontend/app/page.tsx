"use client";

import { useState } from "react";
import styles from "./page.module.css";

// ══════════════════════════════════════════════════════
//  SAMPLE DATA — will be replaced with live API later
// ══════════════════════════════════════════════════════

const METRICS = { totalReviews: 847, avgRating: 3.2, keyThemes: 5, actionItems: 3 };

const RATINGS = [
  { label: "5 STAR", count: 124, pct: 14.6, cls: "star5" },
  { label: "4 STAR", count: 98, pct: 11.5, cls: "star4" },
  { label: "3 STAR", count: 124, pct: 14.6, cls: "star3" },
  { label: "2 STAR", count: 189, pct: 22.3, cls: "star2" },
  { label: "1 STAR", count: 312, pct: 36.8, cls: "star1" },
];

const THEMES = [
  { name: "KYC Verification Delays", hits: 243, pct: 85, severity: "critical" },
  { name: "UPI Payment Failures", hits: 189, pct: 70, severity: "high" },
  { name: "App Crashes on Login", hits: 112, pct: 65, severity: "critical" },
  { name: "Slow Withdrawal Processing", hits: 87, pct: 45, severity: "high" },
  { name: "Poor Customer Support", hits: 64, pct: 35, severity: "medium" },
];

const ACTIONS = [
  { badge: "P0 Impact", badgeCls: "actionBadgeP0", title: "Expedite KYC Queue", desc: "Implement automated document verification to reduce manual backlog by 60%." },
  { badge: "HIGH PRIORITY", badgeCls: "actionBadgeHigh", title: "Stabilize UPI Gateway", desc: "Monitor transaction latency and implement fallback secondary protocols." },
  { badge: "MED IMPACT", badgeCls: "actionBadgeMed", title: "Support AI Chatbot", desc: "Deploy specialized LLM to handle common 'Status' inquiries autonomously." },
];

const TIMELINE = [
  { date: "Jun 2, 2026", reviews: 248, themes: 4, active: true },
  { date: "May 26, 2026", reviews: 192, themes: 5, active: false },
  { date: "May 19, 2026", reviews: 215, themes: 3, active: false },
];

const QUOTES = [
  { text: "Still waiting for my KYC to be approved after 7 days. Customer support is non-existent. Truly frustrating experience.", stars: 1, date: "MAY 28, 2026", severity: "critical" },
  { text: "App crashed three times today during login. UPI payments are hit or miss. Needs urgent fixes.", stars: 2, date: "MAY 25, 2026", severity: "critical" },
  { text: "Interface is clean but functionality is lacking. Withdrawals take forever to process compared to competitors.", stars: 3, date: "MAY 22, 2026", severity: "medium" },
];

// ── Deep Metrics Data ──
const WEEKLY_TREND = [
  { week: "Apr 14", reviews: 156, avgRating: 3.4, sentiment: 42 },
  { week: "Apr 21", reviews: 178, avgRating: 3.1, sentiment: 38 },
  { week: "Apr 28", reviews: 201, avgRating: 2.9, sentiment: 35 },
  { week: "May 5", reviews: 189, avgRating: 3.0, sentiment: 36 },
  { week: "May 12", reviews: 223, avgRating: 2.8, sentiment: 32 },
  { week: "May 19", reviews: 215, avgRating: 3.1, sentiment: 39 },
  { week: "May 26", reviews: 192, avgRating: 3.3, sentiment: 41 },
  { week: "Jun 2", reviews: 248, avgRating: 3.2, sentiment: 40 },
];

const TOP_KEYWORDS = [
  { word: "KYC", count: 312, pct: 100 },
  { word: "payment", count: 245, pct: 78 },
  { word: "crash", count: 198, pct: 63 },
  { word: "withdrawal", count: 167, pct: 53 },
  { word: "support", count: 156, pct: 50 },
  { word: "slow", count: 134, pct: 43 },
  { word: "UPI", count: 128, pct: 41 },
  { word: "update", count: 112, pct: 36 },
  { word: "login", count: 98, pct: 31 },
  { word: "bug", count: 87, pct: 28 },
];

const SENTIMENT_BREAKDOWN = [
  { label: "Negative", pct: 59, color: "var(--error)" },
  { label: "Neutral", pct: 15, color: "var(--on-surface-variant)" },
  { label: "Mixed", pct: 14, color: "var(--secondary)" },
  { label: "Positive", pct: 12, color: "var(--neon-lime)" },
];

// ── Global Reviews Data ──
const ALL_REVIEWS = [
  { id: 1, rating: 1, title: "KYC nightmare", text: "Been waiting 3 weeks for KYC approval. No response from support team at all. This is unacceptable for a financial app.", date: "2026-06-01", theme: "KYC" },
  { id: 2, rating: 1, title: "Payment failed again", text: "UPI payments fail every single time during market hours. Lost trading opportunities because of this.", date: "2026-05-31", theme: "UPI" },
  { id: 3, rating: 2, title: "Crashes constantly", text: "App crashes on login at least twice a day. Have to clear cache and restart. Very frustrating.", date: "2026-05-30", theme: "Crashes" },
  { id: 4, rating: 1, title: "Withdrawal issues", text: "Withdrawal request pending for 5 days now. No update, no communication. Where is my money?", date: "2026-05-29", theme: "Withdrawal" },
  { id: 5, rating: 3, title: "Good UI bad performance", text: "The interface looks great but the actual functionality is terrible. Payments fail, KYC is slow.", date: "2026-05-28", theme: "UPI" },
  { id: 6, rating: 1, title: "Worst customer support", text: "Called support 5 times this week. Each time they say 'we will escalate'. Nothing happens.", date: "2026-05-27", theme: "Support" },
  { id: 7, rating: 2, title: "Can't even login", text: "OTP never arrives on time. By the time it comes, it has already expired. Fix your SMS gateway.", date: "2026-05-26", theme: "Crashes" },
  { id: 8, rating: 4, title: "Decent for beginners", text: "Good app for learning about stocks. The educational content is helpful. Wish the app was more stable though.", date: "2026-05-25", theme: "Positive" },
  { id: 9, rating: 1, title: "Money stuck", text: "Sold stocks 4 days ago. Funds still not in my bank account. This is basically holding my money hostage.", date: "2026-05-24", theme: "Withdrawal" },
  { id: 10, rating: 5, title: "Love the simplicity", text: "Very clean and easy to use. Best app for mutual funds. Just wish they'd fix the occasional glitches.", date: "2026-05-23", theme: "Positive" },
  { id: 11, rating: 1, title: "KYC rejected for no reason", text: "Submitted documents 3 times. Keeps getting rejected without clear reason. PAN card is perfectly valid.", date: "2026-05-22", theme: "KYC" },
  { id: 12, rating: 2, title: "Slow and buggy", text: "App is extremely slow during market hours. Takes 10+ seconds to load portfolio. Unacceptable.", date: "2026-05-21", theme: "Crashes" },
  { id: 13, rating: 3, title: "Mixed feelings", text: "Used to be great. Recent updates have made it worse. More crashes, slower payments. Please fix.", date: "2026-05-20", theme: "Crashes" },
  { id: 14, rating: 1, title: "Fraud alert", text: "Unauthorized transaction appeared on my account. Support is not responding to my complaint.", date: "2026-05-19", theme: "Support" },
  { id: 15, rating: 4, title: "Getting better", text: "Latest update fixed some bugs. KYC was approved in 2 days. Hope they keep improving.", date: "2026-05-18", theme: "Positive" },
];

// ── History Data ──
const HISTORY_REPORTS = [
  {
    week: "Week of Jun 2, 2026", reviews: 248, themes: 4, status: "Complete",
    topTheme: "KYC Verification Delays", sentiment: 40, avgRating: 3.2,
    summary: "KYC delays continue to dominate negative feedback. UPI payment failures spiked during market volatility. Two new action items identified for the engineering team.",
    actions: ["Expedite KYC Queue Processing", "Stabilize UPI Gateway", "Deploy Support Chatbot"],
  },
  {
    week: "Week of May 26, 2026", reviews: 192, themes: 5, status: "Complete",
    topTheme: "UPI Payment Failures", sentiment: 41, avgRating: 3.3,
    summary: "UPI failures were the top complaint this week, correlating with a backend deployment on May 24. App crash reports decreased by 12% after hotfix v4.2.1.",
    actions: ["Rollback UPI gateway config", "Add retry logic for failed transactions"],
  },
  {
    week: "Week of May 19, 2026", reviews: 215, themes: 3, status: "Complete",
    topTheme: "App Crashes on Login", sentiment: 39, avgRating: 3.1,
    summary: "Major spike in crash reports after Android 15 update. Login flow particularly affected. Customer support tickets up 35% week-over-week.",
    actions: ["Android 15 compatibility patch", "Add crashlytics monitoring", "Hire 2 additional support agents"],
  },
  {
    week: "Week of May 12, 2026", reviews: 223, themes: 4, status: "Complete",
    topTheme: "Slow Withdrawal Processing", sentiment: 32, avgRating: 2.8,
    summary: "Withdrawal processing times increased to 4-5 business days due to banking partner issues. Negative sentiment hit an 8-week low at 32%.",
    actions: ["Negotiate SLA with banking partner", "Add withdrawal status tracking", "Proactive email notifications"],
  },
  {
    week: "Week of May 5, 2026", reviews: 189, themes: 3, status: "Complete",
    topTheme: "KYC Verification Delays", sentiment: 36, avgRating: 3.0,
    summary: "KYC backlog grew to 15,000 pending applications. Average approval time increased to 8 days. Positive feedback on new mutual fund features.",
    actions: ["Scale KYC team by 50%", "Implement OCR-based auto-verification"],
  },
];

// ══════════════════════════════════════════════════════
//  COMPONENT
// ══════════════════════════════════════════════════════

type Tab = "dashboard" | "metrics" | "reviews" | "history";

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const [runUrl, setRunUrl] = useState("");

  // Reviews tab state
  const [filterRating, setFilterRating] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // History tab state
  const [expandedReport, setExpandedReport] = useState<number | null>(0);

  const handleTrigger = async () => {
    setStatus("loading");
    setMessage("Triggering pipeline...");
    setRunUrl("");
    try {
      const response = await fetch("/api/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reviewCount: 50, skipScrape: false }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Failed to trigger analysis.");
      setStatus("success");
      setMessage("Pipeline successfully triggered! Analysis is running in the background.");
      if (data.run_url) setRunUrl(data.run_url);
    } catch (error: any) {
      setStatus("error");
      setMessage(error.message);
    }
  };

  const renderStars = (count: number) =>
    Array.from({ length: 5 }, (_, i) => (
      <span key={i} className={`material-symbols-outlined ${i < count ? "fill-icon" : ""}`} style={{ fontSize: 16, color: i < count ? "var(--tertiary)" : "var(--surface-variant)" }}>
        star
      </span>
    ));

  const severityBadge = (severity: string) => {
    const map: Record<string, { cls: string; label: string }> = {
      critical: { cls: styles.badgeCritical, label: "CRITICAL" },
      high: { cls: styles.badgeHigh, label: "HIGH" },
      medium: { cls: styles.badgeMedium, label: "MEDIUM" },
    };
    const s = map[severity] || map.medium;
    return <span className={`${styles.badge} ${s.cls}`}>{s.label}</span>;
  };

  // Filter reviews
  const filteredReviews = ALL_REVIEWS.filter((r) => {
    if (filterRating !== null && r.rating !== filterRating) return false;
    if (searchQuery && !r.text.toLowerCase().includes(searchQuery.toLowerCase()) && !r.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const tabs: { id: Tab; label: string }[] = [
    { id: "dashboard", label: "Dashboard" },
    { id: "metrics", label: "Deep Metrics" },
    { id: "reviews", label: "Global Reviews" },
    { id: "history", label: "History" },
  ];

  // ── Max bar value for chart scaling ──
  const maxWeeklyReviews = Math.max(...WEEKLY_TREND.map((w) => w.reviews));

  return (
    <>
      {/* ── Top Navigation ── */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div className={styles.headerLeft}>
            <span className={styles.logo}>Groww Review Analyst</span>
            <nav className={styles.nav}>
              {tabs.map((t) => (
                <button
                  key={t.id}
                  className={`${styles.navLink} ${activeTab === t.id ? styles.navLinkActive : ""}`}
                  onClick={() => setActiveTab(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </nav>
          </div>
          <div className={styles.headerRight}>
            <button className={styles.primaryBtn} onClick={handleTrigger} disabled={status === "loading"}>
              {status === "loading" ? (
                <><div className={styles.spinner} />Triggering...</>
              ) : (
                <><span className="material-symbols-outlined" style={{ fontSize: 20 }}>analytics</span>Run Analysis Now</>
              )}
            </button>
          </div>
        </div>
      </header>

      <main className={styles.main}>
        {/* ── Status Feedback ── */}
        {status !== "idle" && status !== "loading" && (
          <div className={`${styles.statusCard} ${styles[status]}`} style={{ marginBottom: "2rem" }}>
            <span className={styles.statusTitle}>{status === "success" ? "✓ Success" : "✕ Error"}</span>
            <span className={styles.statusMessage}>{message}</span>
            {status === "success" && runUrl && (
              <a href={runUrl} target="_blank" rel="noopener noreferrer" className={styles.statusLink}>View Pipeline Progress →</a>
            )}
          </div>
        )}

        {/* ════════════════════════════════════════════
            TAB 1: DASHBOARD
        ════════════════════════════════════════════ */}
        {activeTab === "dashboard" && (
          <>
            {/* Overview Metrics */}
            <section className={styles.metricsGrid}>
              {[
                { icon: "reviews", label: "Total Reviews", value: METRICS.totalReviews, suffix: "", colorCls: "cyan" },
                { icon: "star", label: "Avg Rating", value: METRICS.avgRating, suffix: "/5", colorCls: "lime", fill: true },
                { icon: "topic", label: "Key Themes", value: METRICS.keyThemes, suffix: "", colorCls: "pink" },
                { icon: "assignment_late", label: "Action Items", value: METRICS.actionItems, suffix: "", colorCls: "red" },
              ].map((m) => (
                <div key={m.label} className={`${styles.glassCard} ${styles.metricCard}`}>
                  <div className={`${styles.metricIcon} ${styles[m.colorCls]}`}>
                    <span className={`material-symbols-outlined ${m.fill ? "fill-icon" : ""}`} style={{ fontSize: 32 }}>{m.icon}</span>
                  </div>
                  <div>
                    <p className={styles.metricLabel}>{m.label}</p>
                    <h2 className={styles.metricValue}>{m.value}{m.suffix && <span className={styles.metricValueSuffix}>{m.suffix}</span>}</h2>
                  </div>
                </div>
              ))}
            </section>

            {/* Rating + Themes */}
            <div className={styles.midGrid}>
              <section className={`${styles.glassCard} ${styles.sectionCard}`}>
                <div className={styles.sectionHeader}>
                  <h3 className={styles.sectionTitle}>Rating Distribution</h3>
                  <span className={`material-symbols-outlined ${styles.sectionIcon}`}>bar_chart</span>
                </div>
                <div className={styles.ratingRows}>
                  {RATINGS.map((r) => (
                    <div key={r.label} className={styles.ratingRow}>
                      <span className={styles.ratingLabel}>{r.label}</span>
                      <div className={styles.ratingBarTrack}>
                        <div className={`${styles.ratingBarFill} ${styles[r.cls]}`} style={{ width: `${r.pct}%` }} />
                      </div>
                      <span className={styles.ratingCount}>{r.count}</span>
                    </div>
                  ))}
                </div>
              </section>

              <section className={`${styles.glassCard} ${styles.sectionCard}`}>
                <div className={styles.sectionHeader}>
                  <h3 className={styles.sectionTitle}>Neural Theme Analysis</h3>
                  <span className={`material-symbols-outlined ${styles.sectionIcon}`}>psychology</span>
                </div>
                <div className={styles.themesGrid}>
                  {THEMES.map((t) => (
                    <div key={t.name} className={styles.themeCard}>
                      <div className={styles.themeCardHeader}>
                        <span className={styles.themeName}>{t.name}</span>
                        {severityBadge(t.severity)}
                      </div>
                      <div className={styles.themeBar}>
                        <div className={styles.themeBarTrack}>
                          <div className={`${styles.themeBarFill} ${styles[t.severity]}`} style={{ width: `${t.pct}%` }} />
                        </div>
                        <span className={styles.themeHits}>{t.hits} hits</span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            {/* Action Plan + Timeline */}
            <div className={styles.bottomGrid}>
              <section className={`${styles.glassCard} ${styles.sectionCard} ${styles.actionSection}`}>
                <div className={styles.actionGlow} />
                <h3 className={styles.actionTitle}>
                  <span className="material-symbols-outlined" style={{ color: "var(--primary)" }}>auto_fix_high</span>
                  Neural Intelligence Action Plan
                </h3>
                <div className={styles.actionGrid}>
                  {ACTIONS.map((a) => (
                    <div key={a.title} className={styles.actionCard}>
                      <span className={`${styles.actionBadge} ${styles[a.badgeCls]}`}>{a.badge}</span>
                      <h4 className={styles.actionCardTitle}>{a.title}</h4>
                      <p className={styles.actionCardDesc}>{a.desc}</p>
                    </div>
                  ))}
                </div>
              </section>

              <section className={`${styles.glassCard} ${styles.sectionCard}`}>
                <h3 className={styles.sectionTitle} style={{ marginBottom: "2rem" }}>System History</h3>
                <div className={styles.timelineList}>
                  {TIMELINE.map((t) => (
                    <div key={t.date} className={`${styles.timelineItem} ${!t.active ? styles.dimmed : ""}`}>
                      <div>
                        <div className={styles.timelineDate}>{t.date}</div>
                        <div className={styles.timelineMeta}>{t.reviews} REVIEWS • {t.themes} THEMES</div>
                      </div>
                      <span className="material-symbols-outlined" style={{ color: t.active ? "var(--primary)" : "rgba(0, 245, 255, 0.5)", fontSize: 20 }}>check_circle</span>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            {/* Quotes */}
            <section className={styles.quotesSection}>
              <h3 className={styles.sectionTitle} style={{ marginBottom: "2rem" }}>Notable User Intelligence</h3>
              <div className={styles.quotesGrid}>
                {QUOTES.map((q, i) => (
                  <div key={i} className={`${styles.glassCard} ${styles.quoteCard} ${q.severity === "medium" ? styles.medium : ""}`}>
                    <div className={styles.quoteHeader}>
                      <div className={styles.quoteStars}>{renderStars(q.stars)}</div>
                      <span className={styles.quoteDate}>{q.date}</span>
                    </div>
                    <p className={styles.quoteText}>&ldquo;{q.text}&rdquo;</p>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}

        {/* ════════════════════════════════════════════
            TAB 2: DEEP METRICS
        ════════════════════════════════════════════ */}
        {activeTab === "metrics" && (
          <>
            {/* Sentiment Overview Cards */}
            <section className={styles.metricsGrid}>
              {[
                { icon: "trending_down", label: "Negative Sentiment", value: "59%", colorCls: "red" },
                { icon: "sentiment_neutral", label: "Neutral", value: "15%", colorCls: "cyan" },
                { icon: "sentiment_satisfied", label: "Mixed / Positive", value: "26%", colorCls: "lime" },
                { icon: "speed", label: "Sentiment Score", value: "40", colorCls: "pink", suffix: "/100" },
              ].map((m) => (
                <div key={m.label} className={`${styles.glassCard} ${styles.metricCard}`}>
                  <div className={`${styles.metricIcon} ${styles[m.colorCls]}`}>
                    <span className="material-symbols-outlined" style={{ fontSize: 32 }}>{m.icon}</span>
                  </div>
                  <div>
                    <p className={styles.metricLabel}>{m.label}</p>
                    <h2 className={styles.metricValue}>{m.value}{m.suffix && <span className={styles.metricValueSuffix}>{m.suffix}</span>}</h2>
                  </div>
                </div>
              ))}
            </section>

            <div className={styles.midGrid}>
              {/* Weekly Review Volume Chart */}
              <section className={`${styles.glassCard} ${styles.sectionCard}`}>
                <div className={styles.sectionHeader}>
                  <h3 className={styles.sectionTitle}>Weekly Review Volume</h3>
                  <span className={`material-symbols-outlined ${styles.sectionIcon}`}>show_chart</span>
                </div>
                <div className={styles.barChart}>
                  {WEEKLY_TREND.map((w) => (
                    <div key={w.week} className={styles.barCol}>
                      <span className={styles.barValue}>{w.reviews}</span>
                      <div className={styles.bar} style={{ height: `${(w.reviews / maxWeeklyReviews) * 180}px` }} />
                      <span className={styles.barLabel}>{w.week}</span>
                    </div>
                  ))}
                </div>
              </section>

              {/* Top Keywords */}
              <section className={`${styles.glassCard} ${styles.sectionCard}`}>
                <div className={styles.sectionHeader}>
                  <h3 className={styles.sectionTitle}>Top Keywords</h3>
                  <span className={`material-symbols-outlined ${styles.sectionIcon}`}>text_fields</span>
                </div>
                <div className={styles.keywordList}>
                  {TOP_KEYWORDS.map((kw, i) => (
                    <div key={kw.word} className={styles.keywordRow}>
                      <span className={styles.keywordRank}>#{i + 1}</span>
                      <span className={styles.keywordWord}>{kw.word}</span>
                      <div className={styles.keywordBarTrack}>
                        <div className={styles.keywordBarFill} style={{ width: `${kw.pct}%` }} />
                      </div>
                      <span className={styles.keywordCount}>{kw.count}</span>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            {/* Sentiment Breakdown + Weekly Avg Rating */}
            <div className={styles.midGrid}>
              <section className={`${styles.glassCard} ${styles.sectionCard}`}>
                <div className={styles.sectionHeader}>
                  <h3 className={styles.sectionTitle}>Sentiment Breakdown</h3>
                  <span className={`material-symbols-outlined ${styles.sectionIcon}`}>donut_large</span>
                </div>
                <div className={styles.sentimentBars}>
                  {SENTIMENT_BREAKDOWN.map((s) => (
                    <div key={s.label} className={styles.sentimentRow}>
                      <div className={styles.sentimentLabel}>
                        <span className={styles.sentimentDot} style={{ background: s.color }} />
                        <span>{s.label}</span>
                      </div>
                      <div className={styles.sentimentBarTrack}>
                        <div className={styles.sentimentBarFill} style={{ width: `${s.pct}%`, background: s.color, boxShadow: `0 0 8px ${s.color}` }} />
                      </div>
                      <span className={styles.sentimentPct}>{s.pct}%</span>
                    </div>
                  ))}
                </div>
              </section>

              <section className={`${styles.glassCard} ${styles.sectionCard}`}>
                <div className={styles.sectionHeader}>
                  <h3 className={styles.sectionTitle}>Weekly Avg Rating Trend</h3>
                  <span className={`material-symbols-outlined ${styles.sectionIcon}`}>trending_up</span>
                </div>
                <div className={styles.ratingTrend}>
                  {WEEKLY_TREND.map((w) => (
                    <div key={w.week} className={styles.ratingTrendRow}>
                      <span className={styles.ratingTrendWeek}>{w.week}</span>
                      <div className={styles.ratingTrendStars}>
                        {renderStars(Math.round(w.avgRating))}
                      </div>
                      <span className={styles.ratingTrendValue} style={{ color: w.avgRating >= 3.2 ? "var(--neon-lime)" : w.avgRating >= 3.0 ? "var(--secondary)" : "var(--error)" }}>
                        {w.avgRating.toFixed(1)}
                      </span>
                      <span className={styles.ratingTrendSentiment}>
                        {w.sentiment}% pos
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </>
        )}

        {/* ════════════════════════════════════════════
            TAB 3: GLOBAL REVIEWS
        ════════════════════════════════════════════ */}
        {activeTab === "reviews" && (
          <>
            {/* Search + Filter Bar */}
            <div className={styles.reviewControls}>
              <div className={styles.searchBox}>
                <span className="material-symbols-outlined" style={{ color: "var(--on-surface-variant)", fontSize: 20 }}>search</span>
                <input
                  className={styles.searchInput}
                  type="text"
                  placeholder="Search reviews..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <div className={styles.filterChips}>
                <button className={`${styles.filterChip} ${filterRating === null ? styles.filterChipActive : ""}`} onClick={() => setFilterRating(null)}>All</button>
                {[1, 2, 3, 4, 5].map((r) => (
                  <button key={r} className={`${styles.filterChip} ${filterRating === r ? styles.filterChipActive : ""}`} onClick={() => setFilterRating(filterRating === r ? null : r)}>
                    {r}★
                  </button>
                ))}
              </div>
              <span className={styles.reviewCountLabel}>{filteredReviews.length} reviews</span>
            </div>

            {/* Reviews List */}
            <div className={styles.reviewsList}>
              {filteredReviews.map((r) => (
                <div key={r.id} className={`${styles.glassCard} ${styles.reviewCard}`}>
                  <div className={styles.reviewCardHeader}>
                    <div className={styles.reviewCardLeft}>
                      <div className={styles.quoteStars}>{renderStars(r.rating)}</div>
                      <h4 className={styles.reviewCardTitle}>{r.title}</h4>
                    </div>
                    <div className={styles.reviewCardRight}>
                      <span className={`${styles.badge} ${r.rating <= 2 ? styles.badgeCritical : r.rating <= 3 ? styles.badgeMedium : styles.badgeHigh}`}>
                        {r.theme}
                      </span>
                      <span className={styles.reviewCardDate}>{r.date}</span>
                    </div>
                  </div>
                  <p className={styles.reviewCardText}>{r.text}</p>
                </div>
              ))}
            </div>
          </>
        )}

        {/* ════════════════════════════════════════════
            TAB 4: HISTORY
        ════════════════════════════════════════════ */}
        {activeTab === "history" && (
          <>
            <div className={styles.historyHeader}>
              <h2 className={styles.sectionTitle}>
                <span className="material-symbols-outlined" style={{ color: "var(--primary)", verticalAlign: "middle", marginRight: 8 }}>history</span>
                Weekly Report Archive
              </h2>
              <p className={styles.historySubtitle}>Click a report to expand its details and action items.</p>
            </div>

            <div className={styles.historyList}>
              {HISTORY_REPORTS.map((report, i) => (
                <div key={i} className={`${styles.glassCard} ${styles.historyCard} ${expandedReport === i ? styles.historyCardExpanded : ""}`}>
                  <button className={styles.historyCardHeader} onClick={() => setExpandedReport(expandedReport === i ? null : i)}>
                    <div className={styles.historyCardLeft}>
                      <span className="material-symbols-outlined" style={{ color: "var(--primary)", fontSize: 24 }}>check_circle</span>
                      <div>
                        <h4 className={styles.historyCardTitle}>{report.week}</h4>
                        <div className={styles.historyCardMeta}>
                          <span>{report.reviews} reviews</span>
                          <span>•</span>
                          <span>{report.themes} themes</span>
                          <span>•</span>
                          <span>Top: {report.topTheme}</span>
                        </div>
                      </div>
                    </div>
                    <div className={styles.historyCardRight}>
                      <div className={styles.historyStatPill}>
                        <span className="material-symbols-outlined fill-icon" style={{ fontSize: 14, color: "var(--tertiary)" }}>star</span>
                        {report.avgRating}
                      </div>
                      <div className={styles.historyStatPill}>
                        <span className="material-symbols-outlined" style={{ fontSize: 14, color: "var(--secondary)" }}>mood</span>
                        {report.sentiment}%
                      </div>
                      <span className="material-symbols-outlined" style={{ color: "var(--on-surface-variant)", fontSize: 20, transition: "transform 0.2s", transform: expandedReport === i ? "rotate(180deg)" : "rotate(0)" }}>
                        expand_more
                      </span>
                    </div>
                  </button>

                  {expandedReport === i && (
                    <div className={styles.historyCardBody}>
                      <div className={styles.historyDivider} />
                      <p className={styles.historySummary}>{report.summary}</p>
                      <div className={styles.historyActions}>
                        <h5 className={styles.historyActionsTitle}>
                          <span className="material-symbols-outlined" style={{ fontSize: 16, color: "var(--primary)" }}>task_alt</span>
                          Action Items Generated
                        </h5>
                        <ul className={styles.historyActionList}>
                          {report.actions.map((a, j) => (
                            <li key={j} className={styles.historyActionItem}>
                              <span className="material-symbols-outlined" style={{ fontSize: 14, color: "var(--primary)" }}>arrow_right</span>
                              {a}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </main>

      {/* ── Footer ── */}
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerBrand}>
            <span className={styles.footerLogo}>Groww Review Analyst</span>
            <p className={styles.footerCopyright}>© 2026 Groww Review Analyst. All rights reserved.</p>
          </div>
          <div className={styles.footerLinks}>
            <a href="https://github.com/sakethsawant1-star/Milestone3" target="_blank" rel="noopener noreferrer">GitHub</a>
            <a href="https://docs.google.com/document/d/1FEf0bUI499865Tf1gYSSSNZU1s89htr8XW1DNQVr6SA/edit" target="_blank" rel="noopener noreferrer">Google Doc Report</a>
            <a href="#">Settings</a>
          </div>
        </div>
      </footer>
    </>
  );
}
