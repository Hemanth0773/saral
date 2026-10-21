"""
Regression tests for the quality of the structured extraction.

The reported case: a scholarship notice whose Instant Summary showed fragments
copied from headings and partially matched sentences, for example
"Documents needed:Documents needed: necessary documents to their institutions
to enable, match of name of student, bank account number" and
"Step 1:Step 1: PROCEDURE FOR AVAILING THE SCHOLARSHIP".
"""

from app.services import extraction_service


# The notice as described in the bug report: a heading, nine numbered
# clauses (I-IX) and a standalone page marker.
SCHOLARSHIP_PROCEDURE = """3. PROCEDURE FOR AVAILING THE SCHOLARSHIP

I. Students are required to apply annually through the National e-Scholarship Portal. The portal shall remain open for applications as notified by the Commission each year.

II. Incomplete applications will be rejected. The applicant must complete every mandatory field before the final submission, otherwise the form will not be accepted by the portal.

III. The students shall submit the required documents to their institutions to enable, match of name of student, bank account number, and the institution shall upload the same on the portal on behalf of the student.

IV. The bank account of the student must be KYC-compliant. The account must be in the name of the student and must be linked with Aadhaar for the direct benefit transfer.

V. The applicant must provide correct bank details. Any wrong information furnished by the applicant, as per requirement of scheme, will be the sole responsibility of the student.

VI. The institution shall verify the information submitted by the student before uploading the same on the portal.

VII. The institution shall retain the documents for verification for a period of five years from the date of upload. The institution shall produce the documents on demand as and when required by the Commission.

VIII. The University Grants Commission may ask for the documents from the institution for verification at any time and the institution shall comply with such a request without delay.

IX. The student shall upload scanned copies of the certificates along with the application. The documents must be legible and in the prescribed format.

Page 5 of 7
"""


def _all_values(info):
    """Every string the extraction produced, for page marker checks."""
    values = []
    values.extend(doc.name for doc in info.required_documents)
    values.extend(req.requirement for req in info.eligibility_requirements)
    values.extend(cond.condition for cond in info.important_conditions)
    values.extend(step.description for step in info.application_procedure)
    values.extend(amount.amount for amount in info.financial_information)
    values.extend(date.date for date in info.deadlines)
    return values


class TestHeadingsAreNotFacts:
    """A section heading must never become a bullet."""

    def test_the_heading_is_not_a_procedure_step(self):
        steps = extraction_service.extract_application_procedure(SCHOLARSHIP_PROCEDURE)

        assert steps, "the procedure steps should be found"
        for step in steps:
            assert "PROCEDURE FOR AVAILING" not in step.description.upper()
            assert "PROCEDURE FOR AVAILING" not in step.description

    def test_the_heading_is_not_an_eligibility_requirement(self):
        requirements = extraction_service.extract_eligibility_requirements(
            SCHOLARSHIP_PROCEDURE
        )

        for requirement in requirements:
            assert "PROCEDURE FOR AVAILING" not in requirement.requirement

    def test_a_caps_heading_is_rejected(self):
        text = "ELIGIBILITY CRITERIA\n\nThe applicant must be a citizen of India."
        steps = extraction_service.extract_application_procedure(text)

        for step in steps:
            assert step.description != "ELIGIBILITY CRITERIA"


class TestPageMarkersAreNotFacts:
    """A page marker is pagination, not a requirement."""

    def test_the_page_marker_is_not_extracted(self):
        info = extraction_service.extract_structured_information(SCHOLARSHIP_PROCEDURE)

        for value in _all_values(info):
            assert "Page 5 of 7" not in value
            assert "page 5 of 7" not in value.lower()

    def test_a_page_marker_is_not_a_document(self):
        documents = extraction_service.extract_required_documents(
            "The applicant must submit the following documents.\n\nPage 5 of 7"
        )

        for document in documents:
            assert "Page 5" not in document.name

    def test_meaningful_numbers_are_kept(self):
        """Only the page marker is removed, never real content."""
        text = (
            "The applicant must submit the application before 31 December 2026 "
            "with an amount of Rs. 2,50,000. The applicant must be at least "
            "18 years old and the scholarship covers 50% of the fees. "
            "Clause 12 applies. Page 5 of 7"
        )
        info = extraction_service.extract_structured_information(text)

        assert info.deadlines
        assert info.deadlines[0].date == "2026-12-31"
        assert info.financial_information
        assert info.age_requirements
        assert info.percentages


class TestFactsAreCompleteStatements:
    """Facts must be complete, not fragments that stop at a line break."""

    def test_eligibility_requirements_are_complete(self):
        requirements = extraction_service.extract_eligibility_requirements(
            SCHOLARSHIP_PROCEDURE
        )

        for requirement in requirements:
            assert len(requirement.requirement) >= 20
            # A fragment such as "KYC-compliant" is not a requirement.
            assert not requirement.requirement.startswith("KYC-compliant")
            assert not requirement.requirement.startswith(",")
            assert requirement.requirement[0].isupper()

    def test_an_eligibility_rule_is_reported_as_a_complete_statement(self):
        """A rule about who qualifies is a requirement, not a procedure step."""
        text = (
            "1. ELIGIBILITY\n\n"
            "The applicant must have secured at least 60% marks in the qualifying "
            "examination and must be a citizen of India."
        )
        requirements = extraction_service.extract_eligibility_requirements(text)

        assert requirements
        assert requirements[0].requirement.startswith(
            "The applicant must have secured at least 60% marks"
        )
        # The heading itself is not a requirement.
        assert all("ELIGIBILITY" not in r.requirement for r in requirements)

    def test_a_procedure_step_is_not_reported_as_an_eligibility_rule(self):
        """A step of the procedure stays a step."""
        text = (
            "2. PROCEDURE\n\n"
            "3. The applicant must complete every mandatory field before the final "
            "submission."
        )
        requirements = extraction_service.extract_eligibility_requirements(text)
        steps = extraction_service.extract_application_procedure(text)

        assert not requirements
        assert steps
        assert "complete every mandatory field" in steps[0].description

    def test_conditions_are_complete(self):
        text = (
            "Note: The portal will remain closed during the declared holiday. "
            "Any wrong information furnished by the applicant, as per requirement "
            "of scheme, will be the sole responsibility of the student."
        )
        conditions = extraction_service.extract_important_conditions(text)

        assert conditions
        for condition in conditions:
            assert len(condition.condition) >= 20
            assert not condition.condition.startswith(",")
            assert not condition.condition.startswith(" as per requirement")


class TestProcedureSteps:
    """The nine numbered clauses are real steps."""

    def test_the_roman_numbered_clauses_are_captured(self):
        steps = extraction_service.extract_application_procedure(SCHOLARSHIP_PROCEDURE)

        assert len(steps) >= 8
        descriptions = " ".join(step.description for step in steps).lower()
        for topic in (
            "annually through the national e-scholarship portal",
            "incomplete applications will be rejected",
            "kyc-compliant",
            "verify the information",
            "retain the documents",
            "upload scanned copies of the certificates",
        ):
            assert topic in descriptions, f"missing topic: {topic}"

    def test_a_step_is_a_complete_sentence(self):
        steps = extraction_service.extract_application_procedure(SCHOLARSHIP_PROCEDURE)

        for step in steps:
            assert len(step.description) >= 15
            assert step.description[0].isupper()
            assert not step.description.startswith(",")

    def test_the_step_numbering_is_sequential(self):
        steps = extraction_service.extract_application_procedure(SCHOLARSHIP_PROCEDURE)

        assert [step.step_number for step in steps] == list(range(1, len(steps) + 1))


class TestDocumentNames:
    """A document name is a short noun phrase, not a clause."""

    def test_clause_fragments_are_not_documents(self):
        documents = extraction_service.extract_required_documents(SCHOLARSHIP_PROCEDURE)
        names = [document.name for document in documents]

        for name in names:
            assert len(name) <= 60
            assert "shall" not in name.lower()
            assert "must" not in name.lower()
            assert "to their institutions to enable" not in name
            # A fragment that is not a document name is not reported.
            assert "match of name of student" not in name

    def test_the_real_documents_are_still_found(self):
        """A document the source really asks for is reported."""
        text = (
            "The applicant must submit the following documents to the institution: "
            "Aadhaar card, income certificate, bank account details."
        )
        documents = extraction_service.extract_required_documents(text)
        names = " ".join(document.name for document in documents).lower()

        assert "aadhaar" in names
        assert "income certificate" in names
        assert "bank account details" in names

    def test_a_bank_account_condition_is_not_a_required_document(self):
        """Aadhaar as an identifier for the bank account is not a document."""
        text = (
            "The scholarship is directly paid to the students into their bank accounts. "
            "For this their bank account numbers are required to be Aadhaar linked "
            "and verified."
        )
        documents = extraction_service.extract_required_documents(text)

        assert documents == []

    def test_an_ordinary_document_list_still_works(self):
        text = "Applicants must submit Aadhaar, income certificate, and bank account details."
        documents = extraction_service.extract_required_documents(text)
        names = " ".join(document.name for document in documents).lower()

        assert "aadhaar" in names
        assert "income certificate" in names
        assert "bank account details" in names
