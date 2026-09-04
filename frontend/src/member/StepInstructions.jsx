import { BUF_STEP_INSTRUCTIONS } from "@/content/bufStepInstructions";

export const StepInstructions = ({ stepKey }) => {
  const step = BUF_STEP_INSTRUCTIONS[stepKey];
  if (!step) return null;
  return (
    <section className="member-card step-instructions" data-testid={`step-instructions-${stepKey}`}>
      <h2 data-testid={`step-instructions-doing-heading-${stepKey}`}>What You Are Doing In This Step</h2>
      {step.doing.map((paragraph, index) => <p key={index}>{paragraph}</p>)}
      <h2 data-testid={`step-instructions-complete-heading-${stepKey}`}>Complete This Step</h2>
      {step.completeIntro && <p><strong>{step.completeIntro}</strong></p>}
      {step.complete?.length > 0 && (
        <ol>
          {step.complete.map((item, index) => <li key={index}>{item}</li>)}
        </ol>
      )}
      {(step.outro || []).map((paragraph, index) => <p key={`outro-${index}`}><strong>{paragraph}</strong></p>)}
    </section>
  );
};
