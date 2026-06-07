import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const { reviewCount = 50, skipScrape = false } = await request.json();

    const GITHUB_PAT = process.env.GITHUB_PAT;
    const REPO_OWNER = process.env.GITHUB_OWNER || "sakethsawant1-star";
    const REPO_NAME = process.env.GITHUB_REPO || "Milestone3";
    const WORKFLOW_ID = "weekly_review.yml";

    if (!GITHUB_PAT) {
      return NextResponse.json(
        { error: "Missing GITHUB_PAT environment variable. Please configure it in Vercel." },
        { status: 500 }
      );
    }

    // Trigger GitHub Action using the GitHub REST API
    const response = await fetch(
      `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/workflows/${WORKFLOW_ID}/dispatches`,
      {
        method: "POST",
        headers: {
          "Accept": "application/vnd.github.v3+json",
          "Authorization": `token ${GITHUB_PAT}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ref: "master",
          inputs: {
            review_count: reviewCount.toString(),
            skip_scrape: skipScrape.toString(),
          },
        }),
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`GitHub API returned ${response.status}: ${errorText}`);
    }

    // Return the URL where the user can view the run
    return NextResponse.json({
      success: true,
      run_url: `https://github.com/${REPO_OWNER}/${REPO_NAME}/actions`,
    });
  } catch (error: any) {
    console.error("Error triggering workflow:", error);
    return NextResponse.json({ error: error.message || "Failed to trigger analysis" }, { status: 500 });
  }
}
