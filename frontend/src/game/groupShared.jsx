import "./game.css";

export const RoundProgress = ({ current, total }) => (
  <div className="bfg-gg-round-progress" data-testid="bfg-gg-round-progress">
    <span className="bfg-gg-round-label">Round {current} of {total}</span>
    <div className="bfg-gg-dots">
      {Array.from({ length: total }, (_, index) => (
        <span key={index} className={index + 1 < current ? "done" : index + 1 === current ? "current" : ""} />
      ))}
    </div>
  </div>
);

export const RoundResults = ({ results, compact }) => (
  <div className="bfg-gg-results" data-testid="bfg-gg-results">
    {results.filter((item) => item.prioritised).map((item) => (
      <div className="bfg-gg-result prioritised" key={item.idea_id}>
        <span className="bfg-gg-result-rank">{item.rank}</span>
        <div>
          <strong>{item.text}</strong>
          {!compact && <small>Suggested by: {item.suggested_by}</small>}
        </div>
        <span className="bfg-gg-score">Board Score: {item.total_score}</span>
      </div>
    ))}
    {results.some((item) => !item.prioritised) && (
      <>
        <p className="bfg-gg-additional-label">Additional Board Ideas</p>
        {results.filter((item) => !item.prioritised).map((item) => (
          <div className="bfg-gg-result" key={item.idea_id}>
            <span className="bfg-gg-result-rank muted">{item.rank}</span>
            <div>
              <strong>{item.text}</strong>
              {!compact && <small>Suggested by: {item.suggested_by}</small>}
            </div>
          </div>
        ))}
      </>
    )}
  </div>
);
