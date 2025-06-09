"""
Cover Letter Template Generator

This module provides templates for generating professional cover letters with various formats
and styles based on job requirements and company information.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum


class CoverLetterTone(Enum):
    """Cover letter tone options"""
    FORMAL = "formal"
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    ENTHUSIASTIC = "enthusiastic"


class IndustryType(Enum):
    """Industry types for tailored cover letters"""
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    CONSULTING = "consulting"
    ACADEMIA = "academia"
    STARTUP = "startup"
    GOVERNMENT = "government"
    GENERAL = "general"


@dataclass
class ApplicantInfo:
    """Applicant contact information"""
    name: str
    address: str
    email: str
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None


@dataclass
class CompanyInfo:
    """Company/employer information"""
    name: str
    address: str
    hiring_manager: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None  # Mr./Ms./Dr.


@dataclass
class JobInfo:
    """Job position information"""
    title: str
    department: Optional[str] = None
    job_id: Optional[str] = None
    source: Optional[str] = None  # LinkedIn, Indeed, etc.
    start_date: Optional[str] = None
    type: Optional[str] = None  # Internship, Full-time, etc.


@dataclass
class RelevantExperience:
    """Relevant experience to highlight"""
    company: str
    role: str
    duration: str
    key_achievements: List[str]
    technologies_used: Optional[List[str]] = None


@dataclass
class CoverLetterData:
    """Complete cover letter data structure"""
    applicant: ApplicantInfo
    company: CompanyInfo
    job: JobInfo
    relevant_experiences: List[RelevantExperience]
    skills: List[str]
    education: Optional[str] = None
    projects: Optional[List[str]] = None
    motivation: Optional[str] = None
    custom_content: Optional[Dict[str, str]] = None
    industry: IndustryType = IndustryType.GENERAL
    tone: CoverLetterTone = CoverLetterTone.PROFESSIONAL


class BaseCoverLetterTemplate(ABC):
    """Abstract base class for cover letter templates"""
    
    def __init__(self, data: CoverLetterData):
        self.data = data
        self.date = datetime.now().strftime("%B %d, %Y")
    
    @abstractmethod
    def generate(self) -> str:
        """Generate the cover letter content"""
        pass
    
    def _get_salutation(self) -> str:
        """Generate appropriate salutation"""
        if self.data.company.hiring_manager:
            title = self.data.company.title or "Ms."
            return f"Dear {title} {self.data.company.hiring_manager},"
        elif self.data.company.department:
            return f"Dear {self.data.company.department} Team,"
        else:
            return "Dear Hiring Manager,"
    
    def _get_closing(self) -> str:
        """Generate appropriate closing based on tone"""
        if self.data.tone == CoverLetterTone.FORMAL:
            return "Respectfully yours,"
        elif self.data.tone == CoverLetterTone.CASUAL:
            return "Best regards,"
        else:
            return "Sincerely,"
    
    def _format_skills_list(self, skills: List[str], max_skills: int = 5) -> str:
        """Format skills list for natural integration"""
        if len(skills) <= max_skills:
            if len(skills) <= 2:
                return " and ".join(skills)
            else:
                return ", ".join(skills[:-1]) + f", and {skills[-1]}"
        else:
            return ", ".join(skills[:max_skills-1]) + f", and {skills[max_skills-1]}"


class ProfessionalCoverLetterTemplate(BaseCoverLetterTemplate):
    """Standard professional cover letter template"""
    
    def generate(self) -> str:
        """Generate professional cover letter content"""
        sections = []
        
        # Header
        sections.append(self._generate_header())
        
        # Date
        sections.append(self.date)
        
        # Company address
        sections.append(self._generate_company_address())
        
        # Salutation
        sections.append(self._get_salutation())
        
        # Opening paragraph
        sections.append(self._generate_opening())
        
        # Body paragraphs
        sections.append(self._generate_experience_paragraph())
        sections.append(self._generate_skills_paragraph())
        
        # Closing paragraph
        sections.append(self._generate_closing_paragraph())
        
        # Professional closing
        sections.append(self._get_closing())
        sections.append(self.data.applicant.name)
        
        return "\n\n".join(sections)
    
    def _generate_header(self) -> str:
        """Generate applicant header"""
        header_lines = [self.data.applicant.name]
        header_lines.append(self.data.applicant.address)
        header_lines.append(self.data.applicant.email)
        
        return "\n".join(header_lines)
    
    def _generate_company_address(self) -> str:
        """Generate company address section"""
        address_lines = [self.data.company.name]
        address_lines.append(self.data.company.address)
        
        return "\n".join(address_lines)
    
    def _generate_opening(self) -> str:
        """Generate opening paragraph"""
        job_ref = f"the {self.data.job.title}"
        if self.data.job.start_date:
            job_ref += f" starting {self.data.job.start_date}"
        if self.data.job.department:
            job_ref += f" in the {self.data.job.department}"
        
        education_mention = ""
        if self.data.education:
            education_mention = f"As a {self.data.education}, "
        
        opening = f"I am writing to apply for {job_ref} at {self.data.company.name}. "
        opening += f"{education_mention}I am eager to apply my background and experience to this role. "
        
        if self.data.motivation:
            opening += f"{self.data.motivation}"
        else:
            opening += f"I am excited about the opportunity to contribute to your team and help drive {self.data.company.name}'s continued success."
        
        return opening
    
    def _generate_experience_paragraph(self) -> str:
        """Generate experience-focused paragraph"""
        if not self.data.relevant_experiences:
            return self._generate_generic_experience()
        
        main_exp = self.data.relevant_experiences[0]
        
        paragraph = f"During my recent experience as a {main_exp.role} at {main_exp.company}, "
        paragraph += f"I gained valuable experience that directly relates to this position. "
        
        # Add key achievements
        if main_exp.key_achievements:
            if len(main_exp.key_achievements) == 1:
                paragraph += f"In this role, I {main_exp.key_achievements[0].lower()}. "
            else:
                paragraph += f"My responsibilities included {main_exp.key_achievements[0].lower()}, "
                if len(main_exp.key_achievements) > 2:
                    paragraph += f"{', '.join([ach.lower() for ach in main_exp.key_achievements[1:-1]])}, "
                paragraph += f"and {main_exp.key_achievements[-1].lower()}. "
        
        # Add technologies if relevant
        if main_exp.technologies_used:
            tech_list = self._format_skills_list(main_exp.technologies_used)
            paragraph += f"I worked extensively with {tech_list}, which will be valuable for this role."
        
        return paragraph
    
    def _generate_generic_experience(self) -> str:
        """Generate generic experience paragraph when no specific experience provided"""
        return ("Through my academic and professional experiences, I have developed strong analytical "
                "and problem-solving skills that would be valuable in this position. I am passionate "
                "about applying my knowledge to real-world challenges and contributing to innovative solutions.")
    
    def _generate_skills_paragraph(self) -> str:
        """Generate skills and qualifications paragraph"""
        if not self.data.skills:
            return self._generate_generic_skills()
        
        skills_intro = "My technical expertise includes "
        skills_list = self._format_skills_list(self.data.skills)
        
        paragraph = f"{skills_intro}{skills_list}, which align well with the requirements for this position. "
        
        # Add projects if available
        if self.data.projects:
            paragraph += f"I have applied these skills in various projects, including {', '.join(self.data.projects[:2])}. "
        
        # Add learning enthusiasm
        paragraph += ("I am particularly drawn to opportunities where I can continue learning and growing "
                     "while contributing to meaningful projects that drive business value.")
        
        return paragraph
    
    def _generate_generic_skills(self) -> str:
        """Generate generic skills paragraph"""
        return ("I bring strong analytical skills, attention to detail, and a passion for continuous learning. "
                "I thrive in collaborative environments and am excited about the opportunity to contribute "
                "to your team's success while developing my professional skills further.")
    
    def _generate_closing_paragraph(self) -> str:
        """Generate closing paragraph"""
        closing = f"I am enthusiastic about the opportunity to join {self.data.company.name} "
        closing += "and contribute my skills to your innovative team. "
        closing += "Thank you for considering my application. "
        closing += "I would welcome the chance to discuss how my background and enthusiasm make me "
        closing += "a strong fit for this position."
        
        return closing


class TechCoverLetterTemplate(BaseCoverLetterTemplate):
    """Technology-focused cover letter template"""
    
    def generate(self) -> str:
        """Generate tech-focused cover letter"""
        sections = []
        
        # Header
        sections.append(self._generate_header())
        
        # Date
        sections.append(self.date)
        
        # Company address
        sections.append(self._generate_company_address())
        
        # Salutation
        sections.append(self._get_salutation())
        
        # Opening
        sections.append(self._generate_tech_opening())
        
        # Technical experience
        sections.append(self._generate_technical_experience())
        
        # Project highlights
        if self.data.projects:
            sections.append(self._generate_project_highlights())
        
        # Closing
        sections.append(self._generate_tech_closing())
        
        sections.append(self._get_closing())
        sections.append(self.data.applicant.name)
        
        return "\n\n".join(sections)
    
    def _generate_header(self) -> str:
        """Generate header with tech focus"""
        header_lines = [self.data.applicant.name]
        
        contact_info = [self.data.applicant.email]
        if self.data.applicant.phone:
            contact_info.append(self.data.applicant.phone)
        if self.data.applicant.linkedin:
            contact_info.append(f"LinkedIn: {self.data.applicant.linkedin}")
        contact_info.append(self.data.applicant.address)
        
        header_lines.append(" | ".join(contact_info))
        return "\n".join(header_lines)
    
    def _generate_company_address(self) -> str:
        """Generate company address"""
        return f"{self.data.company.name}\n{self.data.company.address}"
    
    def _generate_tech_opening(self) -> str:
        """Generate technology-focused opening"""
        opening = f"I am excited to apply for the {self.data.job.title} position at {self.data.company.name}. "
        
        if self.data.education:
            opening += f"As a {self.data.education}, "
        
        opening += "I am passionate about leveraging technology to solve complex problems and drive innovation. "
        opening += f"Your company's commitment to cutting-edge solutions aligns perfectly with my technical expertise and career aspirations."
        
        return opening
    
    def _generate_technical_experience(self) -> str:
        """Generate technical experience paragraph"""
        if not self.data.relevant_experiences:
            return self._generate_generic_tech_experience()
        
        main_exp = self.data.relevant_experiences[0]
        
        paragraph = f"In my role as {main_exp.role} at {main_exp.company}, "
        paragraph += "I gained hands-on experience with cutting-edge technologies and methodologies. "
        
        if main_exp.technologies_used:
            tech_list = self._format_skills_list(main_exp.technologies_used)
            paragraph += f"I worked extensively with {tech_list}, "
        
        if main_exp.key_achievements:
            paragraph += f"where I {main_exp.key_achievements[0].lower()}. "
            if len(main_exp.key_achievements) > 1:
                additional_achievements = ", ".join([ach.lower() for ach in main_exp.key_achievements[1:]])
                paragraph += f"Additionally, I {additional_achievements}."
        
        return paragraph
    
    def _generate_generic_tech_experience(self) -> str:
        """Generate generic tech experience"""
        skills_mention = ""
        if self.data.skills:
            skills_list = self._format_skills_list(self.data.skills[:3])
            skills_mention = f"My technical toolkit includes {skills_list}, "
        
        return (f"{skills_mention}and I have applied these skills in various academic and personal projects. "
                "I am particularly interested in emerging technologies and stay current with industry trends "
                "through continuous learning and hands-on experimentation.")
    
    def _generate_project_highlights(self) -> str:
        """Generate project highlights paragraph"""
        paragraph = "Some of my notable projects include "
        
        if len(self.data.projects) == 1:
            paragraph += f"{self.data.projects[0]}. "
        elif len(self.data.projects) == 2:
            paragraph += f"{self.data.projects[0]} and {self.data.projects[1]}. "
        else:
            paragraph += f"{', '.join(self.data.projects[:-1])}, and {self.data.projects[-1]}. "
        
        paragraph += ("These experiences have strengthened my problem-solving abilities and taught me "
                     "the importance of writing clean, maintainable code while working effectively in team environments.")
        
        return paragraph
    
    def _generate_tech_closing(self) -> str:
        """Generate technology-focused closing"""
        return (f"I am excited about the opportunity to bring my technical skills and passion for innovation "
                f"to {self.data.company.name}. I would welcome the chance to discuss how my background "
                f"in technology and my enthusiasm for solving complex problems would contribute to your team's success.")


class InternshipCoverLetterTemplate(BaseCoverLetterTemplate):
    """Internship-focused cover letter template"""
    
    def generate(self) -> str:
        """Generate internship cover letter"""
        sections = []
        
        # Header
        sections.append(self._generate_header())
        
        # Date
        sections.append(self.date)
        
        # Company address
        sections.append(self._generate_company_address())
        
        # Salutation
        sections.append(self._get_salutation())
        
        # Opening
        sections.append(self._generate_internship_opening())
        
        # Academic and experience background
        sections.append(self._generate_academic_experience())
        
        # Learning enthusiasm
        sections.append(self._generate_learning_paragraph())
        
        # Closing
        sections.append(self._generate_internship_closing())
        
        sections.append(self._get_closing())
        sections.append(self.data.applicant.name)
        
        return "\n\n".join(sections)
    
    def _generate_header(self) -> str:
        """Generate student-focused header"""
        return f"{self.data.applicant.name}\n{self.data.applicant.address}\n{self.data.applicant.email}"
    
    def _generate_company_address(self) -> str:
        """Generate company address"""
        return f"{self.data.company.name}\n{self.data.company.address}"
    
    def _generate_internship_opening(self) -> str:
        """Generate internship-focused opening"""
        job_ref = f"the {self.data.job.title}"
        if self.data.job.start_date:
            job_ref += f" starting {self.data.job.start_date}"
        
        opening = f"I am writing to apply for {job_ref} at {self.data.company.name}. "
        
        if self.data.education:
            opening += f"As a {self.data.education}, "
        
        opening += "I am eager to apply my academic knowledge to real-world challenges and gain valuable industry experience. "
        opening += f"This internship opportunity aligns perfectly with my career goals and academic focus."
        
        return opening
    
    def _generate_academic_experience(self) -> str:
        """Generate academic and any relevant experience"""
        paragraph = "Through my academic coursework, I have developed a strong foundation in "
        
        if self.data.skills:
            skills_list = self._format_skills_list(self.data.skills[:4])
            paragraph += f"{skills_list}. "
        else:
            paragraph += "analytical thinking and problem-solving. "
        
        # Add any relevant experience
        if self.data.relevant_experiences:
            exp = self.data.relevant_experiences[0]
            paragraph += f"Additionally, my experience as {exp.role} at {exp.company} has given me practical insights into "
            if exp.key_achievements:
                paragraph += f"{exp.key_achievements[0].lower()}. "
        
        # Add projects
        if self.data.projects:
            paragraph += f"I have also applied my skills in projects such as {', '.join(self.data.projects[:2])}, "
            paragraph += "which have enhanced my technical abilities and project management skills."
        
        return paragraph
    
    def _generate_learning_paragraph(self) -> str:
        """Generate learning and growth paragraph"""
        return ("I am particularly excited about this internship because it offers the opportunity to learn from "
                "experienced professionals while contributing to meaningful projects. I am eager to absorb new "
                "knowledge, take on challenges, and grow both personally and professionally. I believe that "
                "combining my academic foundation with hands-on industry experience will enable me to make "
                "valuable contributions to your team.")
    
    def _generate_internship_closing(self) -> str:
        """Generate internship-specific closing"""
        return (f"I am enthusiastic about the opportunity to intern with {self.data.company.name} and contribute "
                "to your team while gaining invaluable professional experience. Thank you for considering my "
                "application. I would welcome the opportunity to discuss how my academic background and "
                "enthusiasm for learning make me a strong candidate for this internship.")


class AcademicCoverLetterTemplate(BaseCoverLetterTemplate):
    """Academic position cover letter template"""
    
    def generate(self) -> str:
        """Generate academic cover letter"""
        sections = []
        
        # Header
        sections.append(self._generate_academic_header())
        
        # Date
        sections.append(self.date)
        
        # Institution address
        sections.append(self._generate_institution_address())
        
        # Salutation
        sections.append(self._get_academic_salutation())
        
        # Opening
        sections.append(self._generate_academic_opening())
        
        # Research experience
        sections.append(self._generate_research_experience())
        
        # Teaching and service
        sections.append(self._generate_teaching_service())
        
        # Closing
        sections.append(self._generate_academic_closing())
        
        sections.append("Sincerely,")
        sections.append(self.data.applicant.name)
        
        return "\n\n".join(sections)
    
    def _generate_academic_header(self) -> str:
        """Generate academic header"""
        header = f"{self.data.applicant.name}\n"
        header += f"{self.data.applicant.address}\n"
        header += f"Email: {self.data.applicant.email}"
        if self.data.applicant.phone:
            header += f" | Phone: {self.data.applicant.phone}"
        return header
    
    def _generate_institution_address(self) -> str:
        """Generate institution address"""
        return f"{self.data.company.name}\n{self.data.company.address}"
    
    def _get_academic_salutation(self) -> str:
        """Generate academic salutation"""
        if self.data.company.hiring_manager:
            return f"Dear Dr. {self.data.company.hiring_manager},"
        else:
            return "Dear Search Committee,"
    
    def _generate_academic_opening(self) -> str:
        """Generate academic opening"""
        return (f"I am writing to apply for the {self.data.job.title} position at {self.data.company.name}. "
                f"My research interests and academic background in {self.data.education or 'my field'} "
                "align well with your department's focus and mission.")
    
    def _generate_research_experience(self) -> str:
        """Generate research experience paragraph"""
        if self.data.relevant_experiences:
            exp = self.data.relevant_experiences[0]
            paragraph = f"My research experience includes work as {exp.role} at {exp.company}, where "
            if exp.key_achievements:
                paragraph += f"I {exp.key_achievements[0].lower()}. "
            paragraph += "This experience has prepared me for the research responsibilities of this position."
        else:
            paragraph = ("Through my graduate studies and research projects, I have developed strong "
                        "analytical and research skills that would be valuable in this academic position.")
        
        return paragraph
    
    def _generate_teaching_service(self) -> str:
        """Generate teaching and service paragraph"""
        return ("I am committed to excellence in both teaching and service. I believe in creating "
                "inclusive learning environments that encourage critical thinking and intellectual growth. "
                "I am also eager to contribute to departmental service and the broader academic community.")
    
    def _generate_academic_closing(self) -> str:
        """Generate academic closing"""
        return (f"I would welcome the opportunity to contribute to {self.data.company.name}'s academic "
                "mission and to discuss how my research and teaching interests align with your department's goals. "
                "Thank you for your consideration.")


class CoverLetterTemplateFactory:
    """Factory class for creating cover letter templates"""
    
    TEMPLATES = {
        'professional': ProfessionalCoverLetterTemplate,
        'tech': TechCoverLetterTemplate,
        'internship': InternshipCoverLetterTemplate,
        'academic': AcademicCoverLetterTemplate,
    }
    
    @classmethod
    def create_template(cls, template_type: str, data: CoverLetterData) -> BaseCoverLetterTemplate:
        """Create a cover letter template of the specified type"""
        if template_type not in cls.TEMPLATES:
            raise ValueError(f"Unknown template type: {template_type}. Available types: {list(cls.TEMPLATES.keys())}")
        
        template_class = cls.TEMPLATES[template_type]
        return template_class(data)
    
    @classmethod
    def available_templates(cls) -> List[str]:
        """Get list of available template types"""
        return list(cls.TEMPLATES.keys())
    
    @classmethod
    def get_recommended_template(cls, job_type: str, industry: IndustryType) -> str:
        """Recommend template based on job type and industry"""
        job_type_lower = job_type.lower()
        
        if 'intern' in job_type_lower:
            return 'internship'
        elif industry == IndustryType.TECHNOLOGY or 'developer' in job_type_lower or 'engineer' in job_type_lower:
            return 'tech'
        elif industry == IndustryType.ACADEMIA or 'research' in job_type_lower or 'professor' in job_type_lower:
            return 'academic'
        else:
            return 'professional'


# Utility functions
def create_sample_cover_letter_data() -> CoverLetterData:
    """Create sample cover letter data for testing"""
    applicant = ApplicantInfo(
        name="Nitanshu Mayur Idnani",
        address="Kapellenstrasse 7, 22117 Hamburg, Germany",
        email="nitanshu.idnani@gmail.com"
    )
    
    company = CompanyInfo(
        name="Würth Elektronik eiSos GmbH & Co. KG",
        address="Clarita-Bernhard-Straße 9, 81249 München, Germany",
        hiring_manager="Rößner",
        title="Ms."
    )
    
    job = JobInfo(
        title="Data Science & Data Analytics internship",
        start_date="September 2025"
    )
    
    experiences = [
        RelevantExperience(
            company="SHILBEY Pvt. Ltd.",
            role="Data Analyst",
            duration="six months",
            key_achievements=[
                "participated in data analysis projects involving complex datasets",
                "built ETL pipelines and automated reporting processes",
                "developed interactive dashboards using Python, SQL and Tableau"
            ],
            technologies_used=["Python", "SQL", "Tableau"]
        )
    ]
    
    skills = ["Python", "SQL", "Apache Kafka", "statistical modeling", "data visualization"]
    
    return CoverLetterData(
        applicant=applicant,
        company=company,
        job=job,
        relevant_experiences=experiences,
        skills=skills,
        education="master's student in Applied Data Science and Analytics at SRH University Hamburg",
        industry=IndustryType.TECHNOLOGY,
        tone=CoverLetterTone.PROFESSIONAL
    )


def generate_cover_letter(template_type: str, cover_letter_data: CoverLetterData) -> str:
    """Generate a cover letter using the specified template and data"""
    try:
        template = CoverLetterTemplateFactory.create_template(template_type, cover_letter_data)
        return template.generate()
    except Exception as e:
        raise Exception(f"Error generating cover letter: {str(e)}")


def auto_select_template(job_title: str, company_industry: str = "general") -> str:
    """Automatically select the best template based on job and company info"""
    try:
        industry = IndustryType(company_industry.lower())
    except ValueError:
        industry = IndustryType.GENERAL
    
    return CoverLetterTemplateFactory.get_recommended_template(job_title, industry)


if __name__ == "__main__":
    # Example usage
    sample_data = create_sample_cover_letter_data()
    
    # Generate different types of cover letters
    for template_type in CoverLetterTemplateFactory.available_templates():
        print(f"\n=== {template_type.upper()} COVER LETTER ===")
        cover_letter_content = generate_cover_letter(template_type, sample_data)
        print(cover_letter_content)
        print("\n" + "="*60)
    
    # Test auto-selection
    print(f"\nRecommended template for 'Software Engineer' in tech: {auto_select_template('Software Engineer', 'technology')}")
    print(f"Recommended template for 'Research Intern': {auto_select_template('Research Intern')}")