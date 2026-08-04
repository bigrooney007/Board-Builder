export const FieldError = ({ name, message }) => message ? <p className="field-error" data-testid={`${name}-error-message`}>{message}</p> : null;

export const TextField = ({ name, label, value, update, error, type = "text", required = true, helper, placeholder }) => (
  <label className="field" data-testid={`${name}-field`}><span>{label}{required && <b> *</b>}</span><input type={type} value={value} placeholder={placeholder} onChange={(event) => update(name, event.target.value)} data-testid={`${name}-input`} min={type === "number" ? "0" : undefined} />{helper && <small data-testid={`${name}-helper-text`}>{helper}</small>}<FieldError name={name} message={error} /></label>
);

export const TextAreaField = ({ name, label, value, update, error, required = true, helper, placeholder }) => (
  <label className="field" data-testid={`${name}-field`}><span>{label}{required && <b> *</b>}</span><textarea rows="4" value={value} placeholder={placeholder} onChange={(event) => update(name, event.target.value)} data-testid={`${name}-textarea`} />{helper && <small data-testid={`${name}-helper-text`}>{helper}</small>}<FieldError name={name} message={error} /></label>
);

export const SelectField = ({ name, label, value, update, error, options }) => (
  <label className="field" data-testid={`${name}-field`}><span>{label} <b>*</b></span><select value={value} onChange={(event) => update(name, event.target.value)} data-testid={`${name}-select`}><option value="">Select one</option>{options.map((option) => <option value={option} key={option}>{option}</option>)}</select><FieldError name={name} message={error} /></label>
);

export const CheckboxGroup = ({ name, label, value, update, error, options }) => {
  const toggle = (option) => update(name, value.includes(option) ? value.filter((item) => item !== option) : [...value, option]);
  return <fieldset className="field choice-field" data-testid={`${name}-field`}><legend>{label} <b>*</b></legend><div className="choice-grid">{options.map((option, index) => <label className={`choice ${value.includes(option) ? "selected" : ""}`} key={option}><input type="checkbox" checked={value.includes(option)} onChange={() => toggle(option)} data-testid={`${name}-option-${index + 1}`} /><span>{option}</span></label>)}</div><FieldError name={name} message={error} /></fieldset>;
};

export const RadioGroup = ({ name, label, value, update, error, options }) => (
  <fieldset className="field choice-field" data-testid={`${name}-field`}><legend>{label} <b>*</b></legend><div className="choice-grid">{options.map((option, index) => <label className={`choice ${value === option ? "selected" : ""}`} key={option}><input type="radio" name={name} value={option} checked={value === option} onChange={() => update(name, option)} data-testid={`${name}-option-${index + 1}`} /><span>{option}</span></label>)}</div><FieldError name={name} message={error} /></fieldset>
);

export const FormActions = ({ onBack, onNext, final = false, submitting = false }) => <div className="form-actions">{onBack && <button className="button button-back" onClick={onBack} type="button" data-testid="assessment-back-button">Back</button>}<button className="button" onClick={onNext} type="button" disabled={submitting} data-testid={final ? "submit-board-assessment-button" : "assessment-next-button"}>{submitting ? "Submitting…" : final ? "Submit My Board Assessment" : "Next"}</button></div>;