# Export and Editing Instructions

## Files intended for editing and sending

- Edit: `Bambu_Lab_Controller_Project_Overview.docx`
- Reference/maintenance source: `Bambu_Lab_Controller_Project_Overview.md`
- Send after personalization: `Bambu_Lab_Controller_Project_Overview.pdf`
- Claim audit: `PROJECT_FACT_CHECK.md`
- Photo checklist: `PROTOTYPE_IMAGE_GUIDE.md`

Recommended external attachment filename:

`Dima_Nova_Horizon_Bambu_Lab_Controller_Overview.pdf`

## Placeholders that must be replaced

Before sending, replace:

- `[INSERT EMAIL]`
- `[INSERT PHONE]`
- `[INSERT PROJECT WEBSITE]`
- `[INSERT GITHUB OR PRIVATE-DEMO LINK, IF SHARED]`
- `[INSERT SOCIAL LINKS]`
- All five image placeholders listed in `PROTOTYPE_IMAGE_GUIDE.md`

Also confirm whether you want to share a public repository link. The repository
now has a local reviewed baseline commit and author identity, but no remote or
license. A source/security review removed known device-specific production
defaults and found no literal credentials. Choose a license and intentionally
review what will be public before creating or sharing a remote repository.

## Inserting prototype images in Word

1. Open `Bambu_Lab_Controller_Project_Overview.docx` in Microsoft Word or a recent LibreOffice Writer.
2. Click the placeholder image and note its displayed size.
3. Delete the placeholder only—not its surrounding table cell or caption.
4. Choose **Insert → Pictures**, select the prepared photo, and keep it **In Line with Text**.
5. Set the new image to the same width as the deleted placeholder. Lock the aspect ratio.
6. Crop the photograph to fill the available space without stretching it.
7. Keep the existing caption directly below the image.
8. Check that the following page still starts with the expected numbered section.

The document is designed as six fixed pages. If an image pushes text to a new page, reduce the image height or restore the placeholder dimensions; do not shrink body text.

## Preserving the layout

- Keep the page size as US Letter and retain the existing margins.
- Use the existing Inter font family when available; LibreOffice may substitute a metrically similar sans-serif font on another machine.
- Do not widen tables or add table columns.
- Keep status labels such as **Verified**, **Partial**, **Planned**, and **HW dependent** unchanged unless the fact-check evidence is updated.
- Avoid adding a Bambu Lab logo unless Bambu Lab supplies it for this purpose and approves its use.
- After editing, inspect all six pages at 100% zoom and export a fresh PDF.

## Regenerating Word and PDF

The package was generated with:

- Python 3
- `python-docx` 1.2.0
- Pillow 11.3.0
- LibreOffice headless PDF export
- Poppler tools (`pdfinfo`, `pdftotext`, `pdftoppm`) for validation

Recreate the isolated tooling and regenerate:

```sh
python3 -m venv /tmp/nh-outreach-doc-venv
/tmp/nh-outreach-doc-venv/bin/pip install python-docx==1.2.0 Pillow==11.3.0
/tmp/nh-outreach-doc-venv/bin/python \
  docs/bambu-lab-outreach/tools/generate_outreach_package.py
libreoffice --headless --convert-to pdf \
  --outdir docs/bambu-lab-outreach \
  docs/bambu-lab-outreach/Bambu_Lab_Controller_Project_Overview.docx
```

If you edit the Word file manually, export the PDF from that edited Word file rather than rerunning the generator, because regeneration replaces the Word document and restores placeholders.

## Validation performed on the generated package

The following checks were run:

```sh
unzip -t docs/bambu-lab-outreach/Bambu_Lab_Controller_Project_Overview.docx
pdfinfo docs/bambu-lab-outreach/Bambu_Lab_Controller_Project_Overview.pdf
pdftotext -layout \
  docs/bambu-lab-outreach/Bambu_Lab_Controller_Project_Overview.pdf \
  /tmp/nh-overview.txt
pdftotext -bbox-layout \
  docs/bambu-lab-outreach/Bambu_Lab_Controller_Project_Overview.pdf \
  /tmp/nh-overview-bbox.html
pdfimages -list \
  docs/bambu-lab-outreach/Bambu_Lab_Controller_Project_Overview.pdf
pdftoppm -png -r 90 \
  docs/bambu-lab-outreach/Bambu_Lab_Controller_Project_Overview.pdf \
  /tmp/nh-overview-pages/page
```

The DOCX archive passed its integrity test and reopened through `python-docx` with editable paragraphs, tables, and inline images. The PDF reports six US Letter pages. Text extraction found every required numbered section. Bounding-box inspection found no words outside page boundaries. Six embedded images were identified: five labeled photograph placeholders and one architecture diagram. Rendered page images were reviewed as a contact sheet for overflow, clipping, table fit, and placeholder visibility. A scan for private network ranges, the development printer identifier, private-key headers, and common API-token patterns returned no matches in the outreach package.

## Which file to attach

Attach the personalized PDF, renamed to:

`Dima_Nova_Horizon_Bambu_Lab_Controller_Overview.pdf`

Do not attach the fact-check file, generator, source repository, or image guide unless Bambu Lab asks for supporting detail. The editable Word file can be retained for follow-up revisions.

## Final pre-send checklist

- [ ] All five prototype photographs are inserted, sharp, and correctly captioned.
- [ ] Email, phone, website, repository choice, and social links are filled in or intentionally removed.
- [ ] No placeholder brackets remain.
- [ ] No IP address, Wi-Fi name, access code, device serial, token, QR code, or private screen content is visible.
- [ ] The document remains exactly six pages unless content was intentionally revised.
- [ ] Tables fit within page margins and no text or captions are clipped.
- [ ] The independence disclaimer appears on the cover and final page.
- [ ] No Bambu Lab logo is used without documented approval.
- [ ] Planned features remain labeled as planned, scaffolded, or unverified.
- [ ] Bambu Lab is not described as an existing partner, sponsor, or endorser.
- [ ] The PDF opens correctly on a second device or viewer.
- [ ] The email request uses “temporary development loan” and does not imply prior agreement.
- [ ] The attachment filename is appropriate for an external recipient.
