# Consistent public entry and admin editing

This change updates the current guided services. It does not change checkout prices, product entitlements, email automation, or the Fundraising Game's questions and meeting engines.

## Customer entry

On `/recruit`, `/strategic-planning` and `/board-recommitment`, Start for Free opens the same compact dialog over the landing page. It asks only for full name, email address and organization name. Continue saves the service lead and opens the current published questions. No account or password is requested.

Direct links to the introductory start routes open that same dialog. Existing saved question links continue opening their original answers. Closing the dialog returns focus to its button. Escape and the close button work without submitting the details.

Question screens show the current question count, question wording, subtitle, answer and navigation. The introductory “free” heading and public access-recovery prompts have been removed. The count is taken from the saved question version, not hardcoded.

Public menu login links have been removed from the homepage, product shells and shared public navigation. Existing secure customer links and legacy authentication mechanisms are preserved for historical purchases. The admin login remains at `/admin`.

## Logo and presentation

The supplied blue logo is stored unchanged at `/nonprofit-board-builder-logo.jpg`. Public brand references use the central `frontend/src/content/branding.js` setting. Header sizing crops only the surrounding whitespace in the page presentation; the uploaded image file is unchanged.

Normal body text uses black on light pages and white on dark sections. Brand accents and button colors are retained. Meet Rooney uses the homepage heading scale and body rhythm, with explicit spacing between Rooney's name and biography.

## Edit questions and their count

1. Open `/admin/services/recruitment`, `/admin/services/board-recommitment`, or `/admin/services/strategic-planning`.
2. Select Entry Questions, or Free Entry Questions for Strategic Planning.
3. Set Number of Questions to Show and click Apply Question Count. Reducing the count archives later active questions. Add Question, Remove Question, reordering, optional/required settings and individual archive controls remain available.
4. Edit each question's wording and subtitle. Save Draft, preview, and Save and Publish Settings.

New customer starts receive the published question count and subtitles. Already started submissions retain their original question versions and answers. Reducing the count does not erase historic answers. At least one active question is required.

## Edit each offer landing page

Select Landing Page Editor in the same service admin. It embeds the existing full landing-page text editor, scoped to that service. Edit its headings, paragraphs, button labels, process steps, resource descriptions and testimonial heading, then Save Home Page Text.

These edits use the same saved content as the public page. Guided-service defaults no longer silently overwrite saved page wording. The historical editor remains compatible with the same records. Each service's page and questions stay independent.

## Board opportunity marketplace

The public marketplace is https://nonprofitboardbuilder.com/board-opportunities. Opportunities appear there when their recruitment campaign is successfully published. Joining the applicant network is a separate entry at https://nonprofitboardbuilder.com/join-a-board.

## Verification

The release workflow runs the existing product checks plus `tests/service_entry_browser.py`. The new browser checks cover the three contact dialogs, actual admin page saving and reload, published question reduction, editable subtitles, completed submissions, public navigation, the supplied logo, desktop/mobile layout and Meet Rooney spacing and contrast. Backend tests verify that all three services preserve historic answers when questions are archived.

Use the final commit and test results in the accompanying handoff for synchronization. Deployment is a separate action performed by the owner.
