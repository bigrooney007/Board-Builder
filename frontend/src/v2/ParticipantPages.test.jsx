import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { AudienceQuestionnaire } from "./ParticipantPages";

global.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock("../public/OpportunityPages", () => ({ ApplicationForm: () => null }));
jest.mock("../funnels/BoardRecommitmentFormPage", () => ({ __esModule: true, default: () => null }));
jest.mock("../game/SpeakButton", () => ({ __esModule: true, default: () => null }));
jest.mock("./api", () => ({ v2Api: {}, errorMessage: () => "Unavailable" }));
jest.mock("./V2Shell", () => ({ __esModule: true, default: ({ children }) => <div>{children}</div>, Loading: () => null, ErrorNotice: ({ error, children }) => error || children ? <p role="alert">{error || children}</p> : null }));

const identity = { full_name: "Casey Example", email: "casey@example.test" };
const fields = [["funder", "why"], ["where"], ["attract"], ["relationship"], ["ask"], ["amount"]];

async function mount(initialAnswers = {}, extraProps = {}) {
  const onDraftChange = jest.fn(); const onSubmit = jest.fn();
  const node = document.createElement("div"); document.body.appendChild(node);
  const root = createRoot(node);
  await act(async () => root.render(<AudienceQuestionnaire initialAnswers={{ ...identity, ...initialAnswers }} onDraftChange={onDraftChange} onSubmit={onSubmit} {...extraProps} />));
  return { node, onDraftChange, onSubmit, cleanup: async () => { await act(async () => root.unmount()); node.remove(); } };
}

async function click(node, selector) {
  await act(async () => node.querySelector(selector).click());
}
async function submitForm(node) {
  await act(async () => node.querySelector("form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
}
async function answer(node, field, value) {
  await act(async () => {
    const input = node.querySelector(`[data-testid="v2-answer-${field}"]`);
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });
}
async function addCompleteAudience(node, category, name) {
  await click(node, `[data-testid="v2-audience-yes-${category}"]`);
  for (const page of fields) {
    for (const field of page) await answer(node, field, field === "funder" ? name : `${name}: ${field}`);
    await submitForm(node);
  }
}

test("each specific audience keeps its complete approach and participants can suggest multiple audiences in every category", async () => {
  const { node, onDraftChange, onSubmit, cleanup } = await mount();
  try {
    await submitForm(node);
    for (const category of ["individuals", "businesses", "grantmakers"]) {
      await addCompleteAudience(node, category, `${category} first audience`);
      expect(node.textContent).toContain("another type");
      await addCompleteAudience(node, category, `${category} second audience`);
      await click(node, `[data-testid="v2-audience-no-${category}"]`);
    }
    expect(node.textContent).toContain("How would you personally be willing to participate");
    await answer(node, "participation", "I can make introductions when we agree on suitable audiences.");
    await submitForm(node);
    await submitForm(node);
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const submitted = onSubmit.mock.calls[0][0];
    expect(submitted.audiences).toHaveLength(6);
    for (const audience of submitted.audiences) {
      expect(audience.why).toBe(`${audience.funder}: why`);
      expect(audience.relationship).toBe(`${audience.funder}: relationship`);
      expect(audience.amount).toBe(`${audience.funder}: amount`);
    }
    expect(submitted.participation).toContain("when we agree");
    expect(onDraftChange.mock.calls.some(([draft]) => draft.audiences?.length === 6)).toBe(true);
  } finally { await cleanup(); }
});

test("all funding categories can be skipped without inventing an audience or assigning a responsibility", async () => {
  const { node, onSubmit, cleanup } = await mount();
  try {
    await submitForm(node);
    for (const category of ["individuals", "businesses", "grantmakers"]) await click(node, `[data-testid="v2-audience-no-${category}"]`);
    await answer(node, "participation", "I am not sure yet. I would like to discuss what would be useful.");
    await submitForm(node);
    await submitForm(node);
    expect(onSubmit.mock.calls[0][0].audiences).toEqual([]);
    expect(onSubmit.mock.calls[0][0].participation).toContain("not sure");
  } finally { await cleanup(); }
});

test("editing a saved audience during collection returns to the same category and preserves different approaches", async () => {
  const { node, onDraftChange, cleanup } = await mount();
  try {
    await submitForm(node);
    await addCompleteAudience(node, "individuals", "Local alumni");
    const edit = [...node.querySelectorAll("details button")].find((button) => button.textContent === "Edit");
    await act(async () => edit.click());
    await answer(node, "why", "They experienced the program themselves.");
    for (let index = 0; index < 6; index += 1) await submitForm(node);
    expect(node.querySelector('[data-testid="v2-audience-yes-individuals"]')).not.toBeNull();
    expect(node.querySelector('[data-testid="v2-fundraising-submit"]')).toBeNull();
    await addCompleteAudience(node, "individuals", "Friends of alumni");
    const draft = onDraftChange.mock.calls.at(-1)[0];
    expect(draft.audiences).toHaveLength(2);
    expect(draft.audiences[0].why).toBe("They experienced the program themselves.");
    expect(draft.audiences[1].why).toBe("Friends of alumni: why");
  } finally { await cleanup(); }
});

test("an unfinished audience must be completed or removed before submission", async () => {
  const { node, onSubmit, cleanup } = await mount({
    audiences: [{ audience_id: "unfinished", category: "individuals", funder: "Past volunteers", why: "", where: "", attract: "", relationship: "", ask: "", amount: "" }],
    participation: "I can discuss the options.",
    _v2_flow: { mode: "review", categoryIndex: 0, step: 0, audienceId: "", returnToReview: false },
  });
  try {
    await submitForm(node);
    expect(onSubmit).not.toHaveBeenCalled();
    expect(node.querySelector('[role="alert"]').textContent).toContain("finish or remove");
    const remove = [...node.querySelectorAll("button")].find((button) => button.textContent === "Remove this audience");
    await act(async () => remove.click());
    await submitForm(node);
    expect(onSubmit.mock.calls[0][0].audiences).toEqual([]);
  } finally { await cleanup(); }
});

test("the leader can reuse an earlier answer for a chosen field without guessed categories or amounts", async () => {
  const { node, onDraftChange, cleanup } = await mount({}, {
    earlierAnswers: { "1": "Former participants and their families" },
    earlierQuestions: { "1": "Who might be interested in funding the mission?" },
  });
  try {
    expect(node.textContent).toContain("Who might be interested in funding the mission?");
    expect(onDraftChange.mock.calls.at(-1)[0].audiences).toEqual([]);
    await submitForm(node);
    await click(node, '[data-testid="v2-audience-yes-individuals"]');
    const useAnswer = [...node.querySelectorAll("button")].find((button) => button.textContent === "Use for specific type of funder");
    await act(async () => useAnswer.click());
    const draft = onDraftChange.mock.calls.at(-1)[0];
    expect(draft.audiences[0].funder).toBe("Former participants and their families");
    expect(draft.audiences[0].category).toBe("individuals");
    expect(draft.audiences[0].why).toBe("");
    expect(draft.audiences[0].amount).toBe("");
  } finally { await cleanup(); }
});

test("going back from a partial audience offers resume or removal before another audience can begin", async () => {
  const { node, onDraftChange, cleanup } = await mount();
  try {
    await submitForm(node);
    await click(node, '[data-testid="v2-audience-yes-individuals"]');
    await answer(node, "funder", "Former volunteers");
    const back = [...node.querySelectorAll("form button")].find((button) => button.textContent === "Back");
    await act(async () => back.click());
    expect(node.querySelector('[data-testid="v2-audience-yes-individuals"]')).toBeNull();
    expect(node.querySelector('[data-testid="v2-audience-no-individuals"]')).toBeNull();
    expect(node.textContent).toContain("Finish the audience you started");
    await click(node, '[data-testid="v2-audience-resume"]');
    expect(node.querySelector('[data-testid="v2-answer-funder"]').value).toBe("Former volunteers");
    expect(onDraftChange.mock.calls.at(-1)[0].audiences).toHaveLength(1);
  } finally { await cleanup(); }
});
