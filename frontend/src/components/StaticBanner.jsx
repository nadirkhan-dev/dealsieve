const REPO = "https://github.com/nadirkhan-dev/dealsieve#readme";

export default function StaticBanner() {
  return (
    <div className="alert alert-info static-banner" role="note">
      <strong>Static preview</strong> with pre-computed results for 13 fictional demo companies.
      Crawling and scoring run in the full app.{" "}
      <a href={REPO} target="_blank" rel="noreferrer">Read the README</a> to run it locally.
    </div>
  );
}
