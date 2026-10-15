// Text-only explanation on the existing checkout pages. It uses their current styling.
export default function OfferTextRoadmap({ copy }) {
  if (!copy) return null;
  return (
    <div className="guided-outcomes" style={{ margin: "24px auto", maxWidth: 760, textAlign: "center" }}
         data-testid="offer-text-roadmap">
      {copy.introduction && <p className="guided-upgrade-copy" style={{ textAlign: "center", margin: "0 auto 20px" }}>{copy.introduction}</p>}
      {copy.stepsHeading && <h2 style={{ marginBottom: 16 }}>{copy.stepsHeading}</h2>}
      {(copy.steps || []).map((step, index) => (
        <p key={index} style={{ margin: "12px auto", maxWidth: 690 }}>
          <strong>{index + 1}. </strong>{step}
        </p>
      ))}
      {copy.closing && <p style={{ marginTop: 20 }}>{copy.closing}</p>}
    </div>
  );
}
