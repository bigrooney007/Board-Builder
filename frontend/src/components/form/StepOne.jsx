import { FormActions, SelectField, TextAreaField, TextField } from "./FormControls";
import { stepOneText } from "../../content/siteContent";

const budgets = ["Less than $50,000", "$50,000–$99,999", "$100,000–$249,999", "$250,000–$499,999", "$500,000–$999,999", "$1 million–$2.9 million", "$3 million or more", "Not sure"];

export const StepOne = ({ data, update, errors, onNext }) => <div className="form-step" data-testid="assessment-step-1">
  <div className="form-title"><p className="eyebrow">Step 1 of 4</p><h1 data-testid="step-1-heading">{stepOneText.tellUsAboutYourOrganization}</h1><p data-testid="step-1-description">{stepOneText.helpUsUnderstandTheMission}</p></div>
  <div className="form-grid two-col"><TextField name="name" label="Your name" value={data.name} update={update} error={errors.name} /><TextField name="email" label="Your email address" type="email" value={data.email} update={update} error={errors.email} /><TextField name="phone" label="Your phone number" type="tel" value={data.phone} update={update} error={errors.phone} helper="We may call you if we are unable to reach you by email." /><TextField name="organization_name" label="Organization name" value={data.organization_name} update={update} error={errors.organization_name} /><TextField name="website" label="Website" type="url" value={data.website} update={update} error={errors.website} required={false} /></div>
  <TextAreaField name="mission" label="What is your organization’s mission?" value={data.mission} update={update} error={errors.mission} />
  <fieldset className="location-group"><legend>{stepOneText.whereIsYourOrganizationLocated}<b>*</b></legend><div className="form-grid three-col"><TextField name="city" label="City" value={data.city} update={update} error={errors.city} /><TextField name="state_region" label="State or region" value={data.state_region} update={update} error={errors.state_region} /><TextField name="country" label="Country" value={data.country} update={update} error={errors.country} /></div></fieldset>
  <SelectField name="annual_budget" label="What is your organization’s approximate annual budget?" value={data.annual_budget} update={update} error={errors.annual_budget} options={budgets} />
  <TextAreaField name="most_important_board_result" label="What is the most important result your organization needs its board to help achieve?" value={data.most_important_board_result} update={update} error={errors.most_important_board_result} placeholder={stepOneText.exampleRaiseMoneyBuildPartnerships} />
  <FormActions onNext={onNext} />
</div>;