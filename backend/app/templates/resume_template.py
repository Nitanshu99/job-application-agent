"""
Resume Template Generator

This module provides templates for generating professional resumes with various formats
and styles. It includes classes for different resume types and customization options.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class ContactInfo:
    """Contact information structure"""
    name: str
    email: str
    phone: str
    address: str
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None


@dataclass
class Education:
    """Education entry structure"""
    degree: str
    institution: str
    location: str
    start_date: str
    end_date: str
    gpa: Optional[str] = None
    coursework: Optional[List[str]] = None
    focus: Optional[str] = None


@dataclass
class Experience:
    """Work experience entry structure"""
    title: str
    company: str
    location: str
    start_date: str
    end_date: str
    responsibilities: List[str]
    achievements: Optional[List[str]] = None


@dataclass
class Project:
    """Project entry structure"""
    name: str
    date: str
    description: str
    technologies: List[str]
    url: Optional[str] = None
    achievements: Optional[List[str]] = None


@dataclass
class ResumeData:
    """Complete resume data structure"""
    contact_info: ContactInfo
    summary: str
    education: List[Education]
    technical_skills: Dict[str, List[str]]
    experience: List[Experience]
    projects: List[Project]
    languages: Optional[Dict[str, str]] = None
    additional_sections: Optional[Dict[str, Any]] = None


class BaseResumeTemplate(ABC):
    """Abstract base class for resume templates"""
    
    def __init__(self, data: ResumeData):
        self.data = data
    
    @abstractmethod
    def generate(self) -> str:
        """Generate the resume content"""
        pass
    
    def format_date_range(self, start_date: str, end_date: str) -> str:
        """Format date range for display"""
        if end_date.lower() in ['present', 'current']:
            return f"{start_date} – Present"
        return f"{start_date} – {end_date}"
    
    def format_technologies(self, technologies: List[str]) -> str:
        """Format technology list"""
        return ", ".join(technologies)


class ProfessionalResumeTemplate(BaseResumeTemplate):
    """Professional resume template with clean formatting"""
    
    def generate(self) -> str:
        """Generate professional resume content"""
        sections = []
        
        # Header
        sections.append(self._generate_header())
        
        # Summary
        if self.data.summary:
            sections.append(self._generate_summary())
        
        # Education
        sections.append(self._generate_education())
        
        # Technical Skills
        sections.append(self._generate_technical_skills())
        
        # Professional Experience
        sections.append(self._generate_experience())
        
        # Projects
        sections.append(self._generate_projects())
        
        # Languages
        if self.data.languages:
            sections.append(self._generate_languages())
        
        # Additional sections
        if self.data.additional_sections:
            sections.append(self._generate_additional_sections())
        
        return "\n\n".join(sections)
    
    def _generate_header(self) -> str:
        """Generate header section"""
        contact = self.data.contact_info
        header_lines = [contact.name]
        
        # Contact details
        contact_details = []
        contact_details.append(f"📧 {contact.email}")
        if contact.phone:
            contact_details.append(f"📱 {contact.phone}")
        contact_details.append(f"📍 {contact.address}")
        if contact.linkedin:
            contact_details.append(f"💼 {contact.linkedin}")
        if contact.github:
            contact_details.append(f"🔗 {contact.github}")
        if contact.website:
            contact_details.append(f"🌐 {contact.website}")
        
        header_lines.append(" | ".join(contact_details))
        return "\n".join(header_lines)
    
    def _generate_summary(self) -> str:
        """Generate summary section"""
        return f"Summary\n{self.data.summary}"
    
    def _generate_education(self) -> str:
        """Generate education section"""
        education_lines = ["Education"]
        
        for edu in self.data.education:
            edu_header = f"{edu.degree}"
            edu_details = f"{edu.institution}, {edu.location} | {self.format_date_range(edu.start_date, edu.end_date)}"
            
            education_lines.append(edu_header)
            education_lines.append(edu_details)
            
            if edu.coursework:
                education_lines.append(f"Coursework: {', '.join(edu.coursework)}")
            
            if edu.focus:
                education_lines.append(f"Focus: {edu.focus}")
            
            if edu.gpa:
                education_lines.append(f"GPA: {edu.gpa}")
            
            education_lines.append("")  # Spacing between entries
        
        return "\n".join(education_lines).rstrip()
    
    def _generate_technical_skills(self) -> str:
        """Generate technical skills section"""
        skills_lines = ["Technical Skills"]
        
        for category, skills in self.data.technical_skills.items():
            skills_line = f"{category}: {', '.join(skills)}"
            skills_lines.append(skills_line)
        
        return "\n".join(skills_lines)
    
    def _generate_experience(self) -> str:
        """Generate professional experience section"""
        exp_lines = ["Professional Experience"]
        
        for exp in self.data.experience:
            # Job title and company
            exp_header = f"{exp.title}"
            exp_details = f"{exp.company}, {exp.location} | {self.format_date_range(exp.start_date, exp.end_date)}"
            
            exp_lines.append(exp_header)
            exp_lines.append(exp_details)
            
            # Responsibilities
            for responsibility in exp.responsibilities:
                exp_lines.append(f"• {responsibility}")
            
            # Achievements
            if exp.achievements:
                for achievement in exp.achievements:
                    exp_lines.append(f"• {achievement}")
            
            exp_lines.append("")  # Spacing between entries
        
        return "\n".join(exp_lines).rstrip()
    
    def _generate_projects(self) -> str:
        """Generate projects section"""
        project_lines = ["Major Projects"]
        
        for project in self.data.projects:
            # Project header
            project_header = f"{project.name} ({project.date})"
            project_lines.append(project_header)
            
            # Description
            project_lines.append(project.description)
            
            # Achievements
            if project.achievements:
                for achievement in project.achievements:
                    project_lines.append(f"• {achievement}")
            
            # Technologies
            tech_line = f"Technologies: {self.format_technologies(project.technologies)}"
            project_lines.append(tech_line)
            
            # URL
            if project.url:
                project_lines.append(f"View Project: {project.url}")
            
            project_lines.append("")  # Spacing between entries
        
        return "\n".join(project_lines).rstrip()
    
    def _generate_languages(self) -> str:
        """Generate languages section"""
        lang_lines = ["Languages"]
        
        for language, level in self.data.languages.items():
            lang_lines.append(f"{language}: {level}")
        
        return "\n".join(lang_lines)
    
    def _generate_additional_sections(self) -> str:
        """Generate additional sections"""
        additional_lines = []
        
        for section_name, content in self.data.additional_sections.items():
            additional_lines.append(section_name)
            
            if isinstance(content, list):
                for item in content:
                    additional_lines.append(f"• {item}")
            elif isinstance(content, str):
                additional_lines.append(content)
            
            additional_lines.append("")
        
        return "\n".join(additional_lines).rstrip()


class AcademicResumeTemplate(BaseResumeTemplate):
    """Academic-focused resume template"""
    
    def generate(self) -> str:
        """Generate academic resume content"""
        sections = []
        
        # Header
        sections.append(self._generate_header())
        
        # Education (prioritized for academic resumes)
        sections.append(self._generate_education())
        
        # Research Experience
        sections.append(self._generate_research_experience())
        
        # Publications
        if self.data.additional_sections and 'publications' in self.data.additional_sections:
            sections.append(self._generate_publications())
        
        # Technical Skills
        sections.append(self._generate_technical_skills())
        
        # Projects
        sections.append(self._generate_projects())
        
        # Professional Experience
        sections.append(self._generate_experience())
        
        return "\n\n".join(sections)
    
    def _generate_header(self) -> str:
        """Generate academic header"""
        contact = self.data.contact_info
        header_lines = [contact.name]
        
        contact_details = []
        contact_details.append(f"Email: {contact.email}")
        if contact.phone:
            contact_details.append(f"Phone: {contact.phone}")
        contact_details.append(f"Address: {contact.address}")
        
        header_lines.append(" | ".join(contact_details))
        return "\n".join(header_lines)
    
    def _generate_education(self) -> str:
        """Generate education section with academic focus"""
        education_lines = ["EDUCATION"]
        
        for edu in self.data.education:
            edu_line = f"{edu.degree}, {edu.institution}"
            education_lines.append(edu_line)
            education_lines.append(f"{edu.location} | {self.format_date_range(edu.start_date, edu.end_date)}")
            
            if edu.gpa:
                education_lines.append(f"GPA: {edu.gpa}")
            
            if edu.coursework:
                education_lines.append(f"Relevant Coursework: {', '.join(edu.coursework)}")
            
            education_lines.append("")
        
        return "\n".join(education_lines).rstrip()
    
    def _generate_research_experience(self) -> str:
        """Generate research experience section"""
        if not any("Research" in exp.title or "Intern" in exp.title for exp in self.data.experience):
            return ""
        
        research_lines = ["RESEARCH EXPERIENCE"]
        
        for exp in self.data.experience:
            if "Research" in exp.title or "Intern" in exp.title:
                research_lines.append(f"{exp.title}")
                research_lines.append(f"{exp.company}, {exp.location} | {self.format_date_range(exp.start_date, exp.end_date)}")
                
                for responsibility in exp.responsibilities:
                    research_lines.append(f"• {responsibility}")
                
                research_lines.append("")
        
        return "\n".join(research_lines).rstrip()
    
    def _generate_publications(self) -> str:
        """Generate publications section"""
        pub_lines = ["PUBLICATIONS"]
        
        publications = self.data.additional_sections.get('publications', [])
        for pub in publications:
            pub_lines.append(f"• {pub}")
        
        return "\n".join(pub_lines)
    
    def _generate_technical_skills(self) -> str:
        """Generate technical skills section"""
        return ProfessionalResumeTemplate._generate_technical_skills(self)
    
    def _generate_projects(self) -> str:
        """Generate projects section"""
        return ProfessionalResumeTemplate._generate_projects(self)
    
    def _generate_experience(self) -> str:
        """Generate professional experience section"""
        exp_lines = ["PROFESSIONAL EXPERIENCE"]
        
        for exp in self.data.experience:
            if "Research" not in exp.title and "Intern" not in exp.title:
                exp_lines.append(f"{exp.title}")
                exp_lines.append(f"{exp.company}, {exp.location} | {self.format_date_range(exp.start_date, exp.end_date)}")
                
                for responsibility in exp.responsibilities:
                    exp_lines.append(f"• {responsibility}")
                
                exp_lines.append("")
        
        return "\n".join(exp_lines).rstrip()


class TechResumeTemplate(BaseResumeTemplate):
    """Technology-focused resume template"""
    
    def generate(self) -> str:
        """Generate tech resume content"""
        sections = []
        
        # Header
        sections.append(self._generate_header())
        
        # Summary/Objective
        if self.data.summary:
            sections.append(self._generate_summary())
        
        # Technical Skills (prioritized)
        sections.append(self._generate_technical_skills())
        
        # Professional Experience
        sections.append(self._generate_experience())
        
        # Projects (prominent in tech resumes)
        sections.append(self._generate_projects())
        
        # Education
        sections.append(self._generate_education())
        
        return "\n\n".join(sections)
    
    def _generate_header(self) -> str:
        """Generate tech-focused header"""
        contact = self.data.contact_info
        header_lines = [contact.name]
        
        contact_details = []
        contact_details.append(contact.email)
        if contact.phone:
            contact_details.append(contact.phone)
        if contact.github:
            contact_details.append(f"GitHub: {contact.github}")
        if contact.linkedin:
            contact_details.append(f"LinkedIn: {contact.linkedin}")
        contact_details.append(contact.address)
        
        header_lines.append(" | ".join(contact_details))
        return "\n".join(header_lines)
    
    def _generate_summary(self) -> str:
        """Generate tech summary"""
        return f"SUMMARY\n{self.data.summary}"
    
    def _generate_technical_skills(self) -> str:
        """Generate comprehensive technical skills section"""
        skills_lines = ["TECHNICAL SKILLS"]
        
        # Prioritize programming languages and frameworks
        priority_categories = [
            "Programming Languages",
            "Programming", 
            "Frameworks", 
            "Databases", 
            "Tools", 
            "Cloud Platforms",
            "Technologies"
        ]
        
        # Add priority categories first
        for category in priority_categories:
            for skill_category, skills in self.data.technical_skills.items():
                if category.lower() in skill_category.lower():
                    skills_line = f"{skill_category}: {', '.join(skills)}"
                    skills_lines.append(skills_line)
                    break
        
        # Add remaining categories
        for skill_category, skills in self.data.technical_skills.items():
            if not any(cat.lower() in skill_category.lower() for cat in priority_categories):
                skills_line = f"{skill_category}: {', '.join(skills)}"
                skills_lines.append(skills_line)
        
        return "\n".join(skills_lines)
    
    def _generate_experience(self) -> str:
        """Generate tech experience with emphasis on technical achievements"""
        return ProfessionalResumeTemplate._generate_experience(self)
    
    def _generate_projects(self) -> str:
        """Generate projects with technical emphasis"""
        project_lines = ["PROJECTS"]
        
        for project in self.data.projects:
            project_header = f"{project.name} ({project.date})"
            project_lines.append(project_header)
            
            # Description
            project_lines.append(project.description)
            
            # Technical achievements
            if project.achievements:
                for achievement in project.achievements:
                    project_lines.append(f"• {achievement}")
            
            # Technologies (prominent)
            tech_line = f"Technologies: {self.format_technologies(project.technologies)}"
            project_lines.append(tech_line)
            
            if project.url:
                project_lines.append(f"Link: {project.url}")
            
            project_lines.append("")
        
        return "\n".join(project_lines).rstrip()
    
    def _generate_education(self) -> str:
        """Generate concise education section"""
        education_lines = ["EDUCATION"]
        
        for edu in self.data.education:
            edu_line = f"{edu.degree} | {edu.institution}, {edu.location} | {self.format_date_range(edu.start_date, edu.end_date)}"
            education_lines.append(edu_line)
            
            if edu.gpa:
                education_lines.append(f"GPA: {edu.gpa}")
        
        return "\n".join(education_lines)


class ResumeTemplateFactory:
    """Factory class for creating resume templates"""
    
    TEMPLATES = {
        'professional': ProfessionalResumeTemplate,
        'academic': AcademicResumeTemplate,
        'tech': TechResumeTemplate,
    }
    
    @classmethod
    def create_template(cls, template_type: str, data: ResumeData) -> BaseResumeTemplate:
        """Create a resume template of the specified type"""
        if template_type not in cls.TEMPLATES:
            raise ValueError(f"Unknown template type: {template_type}. Available types: {list(cls.TEMPLATES.keys())}")
        
        template_class = cls.TEMPLATES[template_type]
        return template_class(data)
    
    @classmethod
    def available_templates(cls) -> List[str]:
        """Get list of available template types"""
        return list(cls.TEMPLATES.keys())


# Example usage and utility functions
def create_sample_resume_data() -> ResumeData:
    """Create sample resume data for testing"""
    contact = ContactInfo(
        name="Nitanshu Idnani",
        email="nitanshu.idnani@gmail.com",
        phone="+49 15560455537",
        address="Kapellenstrasse 7, Hamburg, Hamburg, Germany - 22117",
        linkedin="LinkedIn"
    )
    
    education = [
        Education(
            degree="M.Sc. Applied Data Science and Analytics",
            institution="SRH University",
            location="Hamburg, Germany",
            start_date="October 2024",
            end_date="September 2026",
            coursework=["Machine Learning", "Big Data Analytics", "Statistical Modeling"]
        )
    ]
    
    skills = {
        "Programming": ["Python (Advanced)", "SQL (Advanced)", "R (Learning)", "C/C++ (Learning)"],
        "Data Analysis & ML": ["NumPy", "Pandas", "Scikit-learn", "Matplotlib", "Seaborn", "Plotly"],
        "Databases": ["PostgreSQL", "MongoDB", "Neo4j", "MySQL", "SQLite"]
    }
    
    experience = [
        Experience(
            title="Data Analyst Intern",
            company="SHILBEY Design and Consultancy",
            location="Kadi, India",
            start_date="November 2023",
            end_date="April 2024",
            responsibilities=[
                "Analyzed complex business datasets using Python and SQL",
                "Developed interactive Tableau dashboards for C-Level management"
            ]
        )
    ]
    
    projects = [
        Project(
            name="E-commerce Database Management System",
            date="February 2025",
            description="Designed comprehensive database architecture",
            technologies=["Docker", "PostgreSQL", "MongoDB", "Python"],
            achievements=["Successfully deployed on GCP VM"]
        )
    ]
    
    return ResumeData(
        contact_info=contact,
        summary="Aspiring Data Scientist with strong foundations in Python and analytics.",
        education=education,
        technical_skills=skills,
        experience=experience,
        projects=projects,
        languages={"English": "C1 - Certified", "German": "B1 - Not Certified", "Hindi": "Native"}
    )


def generate_resume(template_type: str, resume_data: ResumeData) -> str:
    """Generate a resume using the specified template and data"""
    try:
        template = ResumeTemplateFactory.create_template(template_type, resume_data)
        return template.generate()
    except Exception as e:
        raise Exception(f"Error generating resume: {str(e)}")


if __name__ == "__main__":
    # Example usage
    sample_data = create_sample_resume_data()
    
    for template_type in ResumeTemplateFactory.available_templates():
        print(f"\n=== {template_type.upper()} RESUME ===")
        resume_content = generate_resume(template_type, sample_data)
        print(resume_content)
        print("\n" + "="*50)