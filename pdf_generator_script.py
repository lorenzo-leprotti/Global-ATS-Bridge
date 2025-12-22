"""
Global ATS Bridge - Random CV Generator
Generates N random international CVs with diverse profiles for comprehensive testing

Requirements:
    pip install reportlab faker
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Frame, PageTemplate, FrameBreak
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib import colors
from faker import Faker
import random
import os
from datetime import datetime, timedelta

# Initialize Faker instances for different locales
faker_locales = {
    'italian': Faker('it_IT'),
    'french': Faker('fr_FR'),
    'german': Faker('de_DE'),
    'indian': Faker('en_IN'),
    'chinese': Faker('zh_CN'),
    'spanish': Faker('es_ES'),
    'portuguese': Faker('pt_PT'),
    'uk': Faker('en_GB')
}

# Country-specific data templates
COUNTRY_CONFIGS = {
    'italian': {
        'degree_types': [
            'Laurea Magistrale in Ingegneria Informatica',
            'Laurea Magistrale in Ingegneria Elettronica',
            'Laurea in Economia e Commercio',
            'Laurea in Scienze Politiche'
        ],
        'undergrad_types': [
            'Laurea Triennale in Ingegneria Informatica',
            'Laurea Triennale in Matematica',
            'Laurea Triennale in Fisica'
        ],
        'universities': [
            'Politecnico di Milano', 'Università di Bologna', 'Sapienza Università di Roma',
            'Università di Padova', 'Politecnico di Torino'
        ],
        'grade_system': lambda: random.choice([
            f"{random.randint(105, 110)}/110",
            "110/110 con Lode (110L)"
        ]),
        'companies': [
            'Tech Solutions SRL', 'Fintech Innovations', 'Leonardo S.p.A.',
            'Intesa Sanpaolo', 'Eni Digital'
        ],
        'phone_format': '+39 3{} {} {} {}',
        'visa_targets': ['F-1 OPT', 'H-1B'],
        'flag': '🇮🇹',
        'headers': {
            'education': 'ISTRUZIONE',
            'experience': 'ESPERIENZE PROFESSIONALI',
            'skills': 'COMPETENZE TECNICHE'
        }
    },
    'french': {
        'degree_types': [
            'Diplôme d\'Ingénieur - Mechanical Engineering',
            'Diplôme d\'Ingénieur - Computer Science',
            'Master en Finance',
            'Master en Data Science'
        ],
        'undergrad_types': [
            'Classes Préparatoires aux Grandes Écoles (CPGE)',
            'Licence en Mathématiques',
            'DUT Informatique'
        ],
        'universities': [
            'École Centrale Paris', 'École Polytechnique', 'HEC Paris',
            'ENSAE Paris', 'Télécom Paris'
        ],
        'grade_system': lambda: f"{random.uniform(14.0, 18.0):.1f}/20",
        'companies': [
            'Renault Group', 'Safran Aircraft Engines', 'Airbus',
            'BNP Paribas', 'Thales Group'
        ],
        'phone_format': '+33 6 {} {} {} {}',
        'visa_targets': ['H-1B', 'L-1'],
        'flag': '🇫🇷',
        'headers': {
            'education': 'FORMATION',
            'experience': 'EXPÉRIENCE PROFESSIONNELLE',
            'skills': 'COMPÉTENCES TECHNIQUES'
        }
    },
    'german': {
        'degree_types': [
            'Master of Science in Computer Science',
            'Master of Engineering in Automotive Engineering',
            'Master in Business Administration',
            'Master in Electrical Engineering'
        ],
        'undergrad_types': [
            'Bachelor of Science in Computer Science',
            'Bachelor of Engineering',
            'Bachelor in Mathematics'
        ],
        'universities': [
            'Technische Universität München', 'RWTH Aachen University',
            'Karlsruhe Institute of Technology', 'Universität Heidelberg',
            'Humboldt-Universität zu Berlin'
        ],
        'grade_system': lambda: random.choice([
            f"{random.uniform(1.0, 1.5):.1f} (Sehr Gut)",
            f"{random.uniform(1.6, 2.5):.1f} (Gut)"
        ]),
        'companies': [
            'Siemens AG', 'BMW Group', 'SAP SE', 'Bosch', 'Volkswagen AG'
        ],
        'phone_format': '+49 1{} {} {} {}',
        'visa_targets': ['H-1B', 'L-1', 'O-1'],
        'flag': '🇩🇪',
        'headers': {
            'education': 'AUSBILDUNG',
            'experience': 'BERUFSERFAHRUNG',
            'skills': 'TECHNISCHE FÄHIGKEITEN'
        }
    },
    'indian': {
        'degree_types': [
            'Master of Technology (M.Tech) in Computer Science',
            'Master of Science (M.S.) in Data Science',
            'Master of Business Administration (MBA)',
            'Master of Engineering (M.E.) in Electronics'
        ],
        'undergrad_types': [
            'Bachelor of Engineering (B.E.) in Information Technology',
            'Bachelor of Technology (B.Tech) in Computer Science',
            'Bachelor of Science (B.Sc.) in Mathematics'
        ],
        'universities': [
            'Indian Institute of Technology (IIT) Bombay',
            'Indian Institute of Technology (IIT) Delhi',
            'Indian Institute of Science (IISc) Bangalore',
            'Birla Institute of Technology and Science (BITS) Pilani',
            'National Institute of Technology (NIT) Trichy'
        ],
        'grade_system': lambda: random.choice([
            f"{random.uniform(8.5, 10.0):.1f}/10 CGPA (First Division with Distinction)",
            f"{random.uniform(70, 85):.1f}% (First Division)"
        ]),
        'companies': [
            'Amazon Development Centre India', 'Microsoft India',
            'Google India', 'Infosys', 'Tata Consultancy Services'
        ],
        'phone_format': '+91 {}{}{}{}{}{}{}{}{}{}',
        'visa_targets': ['F-1 OPT', 'H-1B'],
        'flag': '🇮🇳',
        'headers': {
            'education': 'EDUCATION',
            'experience': 'PROFESSIONAL EXPERIENCE',
            'skills': 'TECHNICAL SKILLS'
        }
    },
    'chinese': {
        'degree_types': [
            'Master of Engineering in Computer Science',
            'Master of Science in Artificial Intelligence',
            'Master in Finance',
            'Master of Engineering in Electrical Engineering'
        ],
        'undergrad_types': [
            'Bachelor of Engineering in Software Engineering',
            'Bachelor of Science in Computer Science',
            'Bachelor in Mathematics'
        ],
        'universities': [
            'Tsinghua University', 'Peking University', 'Fudan University',
            'Shanghai Jiao Tong University', 'Zhejiang University'
        ],
        'grade_system': lambda: f"{random.uniform(85, 95):.1f}/100",
        'companies': [
            'Alibaba Group', 'Tencent', 'ByteDance', 'Huawei', 'Baidu'
        ],
        'phone_format': '+86 1{} {} {} {}',
        'visa_targets': ['F-1 OPT', 'H-1B', 'L-1'],
        'flag': '🇨🇳',
        'headers': {
            'education': 'EDUCATION',
            'experience': 'PROFESSIONAL EXPERIENCE',
            'skills': 'TECHNICAL SKILLS'
        }
    },
    'spanish': {
        'degree_types': [
            'Máster en Ingeniería Informática',
            'Máster en Ciencia de Datos',
            'Máster en Administración de Empresas (MBA)',
            'Máster en Ingeniería Industrial'
        ],
        'undergrad_types': [
            'Grado en Ingeniería Informática',
            'Grado en Matemáticas',
            'Grado en Física'
        ],
        'universities': [
            'Universidad Politécnica de Madrid', 'Universidad de Barcelona',
            'Universidad Autónoma de Madrid', 'Universidad Carlos III de Madrid',
            'ESADE Business School'
        ],
        'grade_system': lambda: f"{random.uniform(7.5, 9.5):.1f}/10 (Sobresaliente)",
        'companies': [
            'Telefónica', 'Banco Santander', 'Inditex', 'Repsol', 'BBVA'
        ],
        'phone_format': '+34 6{} {} {} {}',
        'visa_targets': ['H-1B', 'L-1'],
        'flag': '🇪🇸',
        'headers': {
            'education': 'FORMACIÓN ACADÉMICA',
            'experience': 'EXPERIENCIA PROFESIONAL',
            'skills': 'HABILIDADES TÉCNICAS'
        }
    },
    'portuguese': {
        'degree_types': [
            'Mestrado em Engenharia Informática',
            'Mestrado em Ciência de Dados',
            'Mestrado em Administração de Empresas (MBA)',
            'Mestrado em Engenharia Elétrica'
        ],
        'undergrad_types': [
            'Licenciatura em Engenharia Informática',
            'Licenciatura em Matemática',
            'Licenciatura em Física'
        ],
        'universities': [
            'Universidade de Lisboa', 'Universidade do Porto',
            'Instituto Superior Técnico', 'Universidade de Coimbra',
            'Universidade Nova de Lisboa'
        ],
        'grade_system': lambda: f"{random.randint(16, 19)}/20",
        'companies': [
            'Galp Energia', 'EDP Portugal', 'NOS', 'Jerónimo Martins', 'CGD'
        ],
        'phone_format': '+351 9{} {} {} {}',
        'visa_targets': ['H-1B', 'L-1'],
        'flag': '🇵🇹',
        'headers': {
            'education': 'FORMAÇÃO ACADÉMICA',
            'experience': 'EXPERIÊNCIA PROFISSIONAL',
            'skills': 'COMPETÊNCIAS TÉCNICAS'
        }
    },
    'uk': {
        'degree_types': [
            'Master of Science (MSc) in Computer Science',
            'Master of Engineering (MEng) in Electrical Engineering',
            'Master of Business Administration (MBA)',
            'Master of Arts (MA) in Economics'
        ],
        'undergrad_types': [
            'Bachelor of Science (BSc) in Computer Science',
            'Bachelor of Engineering (BEng)',
            'Bachelor of Arts (BA) in Economics'
        ],
        'universities': [
            'University of Oxford', 'University of Cambridge',
            'Imperial College London', 'University College London',
            'University of Edinburgh'
        ],
        'grade_system': lambda: random.choice([
            'First-Class Honours',
            'Upper Second-Class Honours (2:1)',
            'Lower Second-Class Honours (2:2)'
        ]),
        'companies': [
            'HSBC Holdings', 'BP plc', 'Rolls-Royce', 'GlaxoSmithKline',
            'ARM Holdings'
        ],
        'phone_format': '+44 7{} {} {} {}',
        'visa_targets': ['H-1B', 'L-1', 'O-1'],
        'flag': '🇬🇧',
        'headers': {
            'education': 'EDUCATION',
            'experience': 'PROFESSIONAL EXPERIENCE',
            'skills': 'TECHNICAL SKILLS'
        }
    }
}

TECH_SKILLS = {
    'languages': ['Python', 'Java', 'JavaScript', 'C++', 'Go', 'Rust', 'TypeScript', 'Ruby', 'PHP', 'Swift', 'Kotlin'],
    'frameworks': ['React', 'Angular', 'Vue.js', 'Node.js', 'Django', 'Flask', 'Spring Boot', 'FastAPI', '.NET'],
    'databases': ['PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'DynamoDB', 'Cassandra', 'Oracle'],
    'cloud': ['AWS', 'Azure', 'Google Cloud', 'Heroku', 'DigitalOcean'],
    'tools': ['Docker', 'Kubernetes', 'Git', 'Jenkins', 'CircleCI', 'Terraform', 'Ansible'],
    'ml': ['TensorFlow', 'PyTorch', 'scikit-learn', 'Keras', 'Pandas', 'NumPy']
}

# Native language job titles and experience bullets
LOCALIZED_CONTENT = {
    'italian': {
        'job_titles': [
            'Ingegnere del Software', 'Ingegnere del Software Senior', 'Data Scientist',
            'Ingegnere Machine Learning', 'DevOps Engineer', 'Sviluppatore Full Stack',
            'Ingegnere Backend', 'Sviluppatore Frontend', 'Architetto Cloud', 'Responsabile Tecnico'
        ],
        'bullets': [
            "Sviluppato sistema di {tech} servendo oltre {num}K utenti giornalieri con riduzione della latenza del {perc}%",
            "Guidato team di {team} ingegneri nella migrazione verso architettura cloud, riducendo i costi del {perc}%",
            "Implementato pipeline CI/CD con Docker e Kubernetes, migliorando la velocità di deployment del {perc}%",
            "Ottimizzato query database riducendo i tempi di risposta da {old}s a {new}ms",
            "Progettato e realizzato sistema di raccomandazione con accuratezza del {perc}%",
            "Gestito budget di €{budget}K per infrastruttura cloud e sviluppo prodotto",
            "Collaborato con team internazionali per delivery di features critiche in ambienti Agile",
            "Automatizzato processi di testing riducendo bug in produzione del {perc}%"
        ]
    },
    'french': {
        'job_titles': [
            'Ingénieur Logiciel', 'Ingénieur Logiciel Senior', 'Data Scientist',
            'Ingénieur Machine Learning', 'Ingénieur DevOps', 'Développeur Full Stack',
            'Ingénieur Backend', 'Développeur Frontend', 'Architecte Cloud', 'Chef de Projet Technique'
        ],
        'bullets': [
            "Développé système de {tech} desservant plus de {num}K utilisateurs quotidiens avec réduction de latence de {perc}%",
            "Dirigé équipe de {team} ingénieurs dans migration vers architecture cloud, réduisant les coûts de {perc}%",
            "Implémenté pipeline CI/CD avec Docker et Kubernetes, améliorant la vitesse de déploiement de {perc}%",
            "Optimisé requêtes base de données réduisant temps de réponse de {old}s à {new}ms",
            "Conçu et développé système de recommandation avec précision de {perc}%",
            "Géré budget de €{budget}K pour infrastructure cloud et développement produit",
            "Collaboré avec équipes internationales pour livraison de fonctionnalités critiques en environnement Agile",
            "Automatisé processus de tests réduisant bugs en production de {perc}%"
        ]
    },
    'german': {
        'job_titles': [
            'Software-Ingenieur', 'Senior Software-Ingenieur', 'Data Scientist',
            'Machine Learning Ingenieur', 'DevOps-Ingenieur', 'Full-Stack-Entwickler',
            'Backend-Ingenieur', 'Frontend-Entwickler', 'Cloud-Architekt', 'Technischer Leiter'
        ],
        'bullets': [
            "Entwicklung von {tech}-System für über {num}K tägliche Benutzer mit Latenzreduzierung um {perc}%",
            "Leitung eines Teams von {team} Ingenieuren bei Cloud-Migration, Kostensenkung um {perc}%",
            "Implementierung der CI/CD-Pipeline mit Docker und Kubernetes, Verbesserung der Deployment-Geschwindigkeit um {perc}%",
            "Optimierung von Datenbankabfragen, Reduzierung der Antwortzeit von {old}s auf {new}ms",
            "Entwurf und Entwicklung eines Empfehlungssystems mit {perc}% Genauigkeit",
            "Verwaltung eines Budgets von €{budget}K für Cloud-Infrastruktur und Produktentwicklung",
            "Zusammenarbeit mit internationalen Teams zur Bereitstellung kritischer Features in agilen Umgebungen",
            "Automatisierung von Testprozessen, Reduzierung von Produktionsfehlern um {perc}%"
        ]
    },
    'spanish': {
        'job_titles': [
            'Ingeniero de Software', 'Ingeniero de Software Senior', 'Científico de Datos',
            'Ingeniero de Machine Learning', 'Ingeniero DevOps', 'Desarrollador Full Stack',
            'Ingeniero Backend', 'Desarrollador Frontend', 'Arquitecto Cloud', 'Responsable Técnico'
        ],
        'bullets': [
            "Desarrollado sistema de {tech} sirviendo más de {num}K usuarios diarios con reducción de latencia del {perc}%",
            "Liderado equipo de {team} ingenieros en migración a arquitectura cloud, reduciendo costos en {perc}%",
            "Implementado pipeline CI/CD con Docker y Kubernetes, mejorando velocidad de deployment en {perc}%",
            "Optimizado queries de base de datos reduciendo tiempo de respuesta de {old}s a {new}ms",
            "Diseñado y desarrollado sistema de recomendación con precisión del {perc}%",
            "Gestionado presupuesto de €{budget}K para infraestructura cloud y desarrollo de producto",
            "Colaborado con equipos internacionales para entrega de funcionalidades críticas en entornos Agile",
            "Automatizado procesos de testing reduciendo bugs en producción en {perc}%"
        ]
    },
    'portuguese': {
        'job_titles': [
            'Engenheiro de Software', 'Engenheiro de Software Sênior', 'Cientista de Dados',
            'Engenheiro de Machine Learning', 'Engenheiro DevOps', 'Desenvolvedor Full Stack',
            'Engenheiro Backend', 'Desenvolvedor Frontend', 'Arquiteto Cloud', 'Responsável Técnico'
        ],
        'bullets': [
            "Desenvolvido sistema de {tech} servindo mais de {num}K usuários diários com redução de latência de {perc}%",
            "Liderado equipe de {team} engenheiros na migração para arquitetura cloud, reduzindo custos em {perc}%",
            "Implementado pipeline CI/CD com Docker e Kubernetes, melhorando velocidade de deployment em {perc}%",
            "Otimizado queries de base de dados reduzindo tempo de resposta de {old}s para {new}ms",
            "Projetado e desenvolvido sistema de recomendação com precisão de {perc}%",
            "Gerenciado orçamento de €{budget}K para infraestrutura cloud e desenvolvimento de produto",
            "Colaborado com equipes internacionais para entrega de funcionalidades críticas em ambientes Agile",
            "Automatizado processos de testes reduzindo bugs em produção em {perc}%"
        ]
    },
    'indian': {
        'job_titles': [
            'Software Engineer', 'Senior Software Engineer', 'Data Scientist',
            'Machine Learning Engineer', 'DevOps Engineer', 'Full Stack Developer',
            'Backend Engineer', 'Frontend Developer', 'Cloud Architect', 'Technical Lead'
        ],
        'bullets': [
            "Developed {tech} system serving {num}K+ daily users with {perc}% latency reduction",
            "Led team of {team} engineers in cloud migration, reducing costs by {perc}%",
            "Implemented CI/CD pipeline with Docker and Kubernetes, improving deployment speed by {perc}%",
            "Optimized database queries reducing response time from {old}s to {new}ms",
            "Designed and developed recommendation system with {perc}% accuracy",
            "Managed budget of ${budget}K for cloud infrastructure and product development",
            "Collaborated with cross-functional teams to deliver critical features in Agile environments",
            "Automated testing processes reducing production bugs by {perc}%"
        ]
    },
    'chinese': {
        'job_titles': [
            '软件工程师', '高级软件工程师', '数据科学家',
            '机器学习工程师', 'DevOps工程师', '全栈开发工程师',
            '后端工程师', '前端开发工程师', '云架构师', '技术主管'
        ],
        'bullets': [
            "开发{tech}系统，服务{num}K+日活用户，延迟降低{perc}%",
            "带领{team}名工程师完成云迁移项目，成本降低{perc}%",
            "实施Docker和Kubernetes CI/CD流水线，部署速度提升{perc}%",
            "优化数据库查询，响应时间从{old}秒降至{new}毫秒",
            "设计并开发推荐系统，准确率达{perc}%",
            "管理¥{budget}万预算，用于云基础设施和产品开发",
            "与跨职能团队协作，在敏捷环境中交付关键功能",
            "自动化测试流程，生产环境bug减少{perc}%"
        ]
    },
    'uk': {
        'job_titles': [
            'Software Engineer', 'Senior Software Engineer', 'Data Scientist',
            'Machine Learning Engineer', 'DevOps Engineer', 'Full Stack Developer',
            'Backend Engineer', 'Frontend Developer', 'Cloud Architect', 'Technical Lead'
        ],
        'bullets': [
            "Developed {tech} system serving {num}K+ daily users with {perc}% latency reduction",
            "Led team of {team} engineers in cloud migration, reducing costs by {perc}%",
            "Implemented CI/CD pipeline with Docker and Kubernetes, improving deployment speed by {perc}%",
            "Optimised database queries reducing response time from {old}s to {new}ms",
            "Designed and developed recommendation system with {perc}% accuracy",
            "Managed budget of £{budget}K for cloud infrastructure and product development",
            "Collaborated with cross-functional teams to deliver critical features in Agile environments",
            "Automated testing processes reducing production bugs by {perc}%"
        ]
    }
}

def random_phone(country):
    """Generate random phone number based on country format"""
    config = COUNTRY_CONFIGS[country]
    digits = [str(random.randint(0, 9)) for _ in range(10)]
    return config['phone_format'].format(*digits)

def random_date_range(years_ago_start, years_ago_end):
    """Generate random date range"""
    end_date = datetime.now() - timedelta(days=365 * years_ago_end)
    start_date = end_date - timedelta(days=365 * random.randint(2, 5))
    return start_date.strftime('%B %Y'), end_date.strftime('%B %Y')

def draw_profile_photo_placeholder(canvas_obj, x, y, width, height):
    """Draw a grey rectangle to simulate a profile photo"""
    canvas_obj.setFillColor(colors.HexColor('#CCCCCC'))
    canvas_obj.rect(x, y, width, height, fill=1, stroke=0)

def draw_skill_bar(canvas_obj, x, y, width, proficiency, skill_name):
    """Draw a graphical skill bar (proficiency 0-100)"""
    max_bar_width = width
    bar_height = 12

    # Background bar (light grey)
    canvas_obj.setFillColor(colors.HexColor('#E0E0E0'))
    canvas_obj.rect(x, y, max_bar_width, bar_height, fill=1, stroke=0)

    # Proficiency bar (dark grey/blue)
    fill_width = (proficiency / 100.0) * max_bar_width
    canvas_obj.setFillColor(colors.HexColor('#4A90E2'))
    canvas_obj.rect(x, y, fill_width, bar_height, fill=1, stroke=0)

    # Skill name label
    canvas_obj.setFillColor(colors.black)
    canvas_obj.setFont('Times-Roman', 9)
    canvas_obj.drawString(x, y + bar_height + 2, skill_name)

def generate_experience_bullets(nationality, count=5):
    """Generate realistic experience bullets in native language"""
    localized = LOCALIZED_CONTENT[nationality]
    tech_options = ['microservices', 'API', 'cloud', 'machine learning']

    bullets = []
    templates = localized['bullets']

    for _ in range(min(count, len(templates))):
        template = random.choice(templates)
        bullet = template.format(
            tech=random.choice(tech_options),
            num=random.randint(100, 999),
            perc=random.randint(20, 60),
            team=random.randint(3, 10),
            old=random.randint(2, 10),
            new=random.randint(100, 900),
            budget=random.randint(500, 5000)
        )
        bullets.append(bullet)
        templates = [t for t in templates if t != template]  # Avoid repeats

    return bullets

def generate_random_cv(nationality, output_dir='test_cvs'):
    """Generate a single random CV for given nationality"""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Get country config and faker
    config = COUNTRY_CONFIGS[nationality]
    fake = faker_locales[nationality]
    
    # Generate random profile
    name = fake.name()
    age = random.randint(24, 38)
    email = name.lower().replace(' ', '.') + '@' + random.choice(['gmail.com', 'email.com', 'outlook.com'])
    phone = random_phone(nationality)
    
    if nationality == 'italian':
        location = random.choice(['Milano', 'Roma', 'Bologna', 'Torino', 'Firenze']) + ', Italy'
    elif nationality == 'french':
        location = random.choice(['Paris', 'Lyon', 'Marseille', 'Toulouse', 'Nice']) + ', France'
    elif nationality == 'german':
        location = random.choice(['Berlin', 'München', 'Hamburg', 'Frankfurt', 'Stuttgart']) + ', Germany'
    elif nationality == 'indian':
        location = random.choice(['Bangalore', 'Mumbai', 'Hyderabad', 'Pune', 'Delhi']) + ', India'
    elif nationality == 'chinese':
        location = random.choice(['Beijing', 'Shanghai', 'Shenzhen', 'Hangzhou', 'Guangzhou']) + ', China'
    elif nationality == 'spanish':
        location = random.choice(['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Bilbao']) + ', Spain'
    elif nationality == 'portuguese':
        location = random.choice(['Lisboa', 'Porto', 'Coimbra', 'Braga', 'Faro']) + ', Portugal'
    elif nationality == 'uk':
        location = random.choice(['London', 'Manchester', 'Edinburgh', 'Birmingham', 'Cambridge']) + ', UK'
    else:
        location = fake.city() + ', ' + fake.country()
    
    linkedin = f"linkedin.com/in/{name.lower().replace(' ', '')}"
    
    # Education
    has_masters = random.random() > 0.3
    master_degree = random.choice(config['degree_types']) if has_masters else None
    bachelor_degree = random.choice(config['undergrad_types'])
    master_uni = random.choice(config['universities']) if has_masters else None
    bachelor_uni = random.choice(config['universities'])
    master_grade = config['grade_system']() if has_masters else None
    bachelor_grade = config['grade_system']()

    # Experience (4-7 positions for longer CVs)
    num_positions = random.randint(4, 7)
    years_experience = age - 22
    
    # Skills
    num_langs = random.randint(3, 6)
    num_frameworks = random.randint(2, 4)
    num_tools = random.randint(4, 7)
    
    selected_skills = (
        random.sample(TECH_SKILLS['languages'], num_langs) +
        random.sample(TECH_SKILLS['frameworks'], num_frameworks) +
        random.sample(TECH_SKILLS['tools'], num_tools) +
        random.sample(TECH_SKILLS['databases'], 3) +
        random.sample(TECH_SKILLS['cloud'], 2)
    )
    
    # Get localized headers
    headers = config['headers']

    # Build PDF
    filename = f"{output_dir}/cv_{nationality}_{name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    # RANDOM LAYOUT CHOICE: 50/50 between single-column and two-column
    use_two_column = random.choice([True, False])

    #Prepare skill bars data (with random proficiency)
    skill_bars_data = [(skill, random.randint(60, 95)) for skill in selected_skills[:8]]  # Limit to 8 for visual clarity

    # Custom canvas class to add profile photo
    class CVCanvas(pdf_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            pdf_canvas.Canvas.__init__(self, *args, **kwargs)
            self.add_profile_photo = random.choice([True, False])  # 50% chance

        def showPage(self):
            # Only add photo on first page
            if self._pageNumber == 0 and self.add_profile_photo:
                # Draw profile photo placeholder in top-right
                photo_size = 80
                page_width, page_height = letter
                draw_profile_photo_placeholder(
                    self,
                    page_width - 0.75*inch - photo_size,
                    page_height - 0.75*inch - photo_size - 10,
                    photo_size,
                    photo_size
                )
            pdf_canvas.Canvas.showPage(self)

    if use_two_column:
        # TWO-COLUMN LAYOUT using Frames
        doc = SimpleDocTemplate(
            filename,
            pagesize=letter,
            leftMargin=0.5*inch,
            rightMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )

        # Define frames: narrow sidebar on left, main content on right
        page_width, page_height = letter
        frame_width = page_width - inch

        sidebar_width = 2.2*inch
        main_width = frame_width - sidebar_width - 0.2*inch

        frame_left = Frame(
            0.5*inch,
            0.5*inch,
            sidebar_width,
            page_height - inch,
            id='left',
            showBoundary=0
        )

        frame_right = Frame(
            0.5*inch + sidebar_width + 0.2*inch,
            0.5*inch,
            main_width,
            page_height - inch,
            id='right',
            showBoundary=0
        )

        template = PageTemplate(id='TwoCol', frames=[frame_left, frame_right], onPage=lambda c, d: None)
        doc.addPageTemplates([template])

    else:
        # SINGLE-COLUMN LAYOUT (traditional)
        doc = SimpleDocTemplate(
            filename,
            pagesize=letter,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
            canvasmaker=CVCanvas
        )

    story = []

    # Styles
    name_style = ParagraphStyle(
        'Name',
        fontName='Times-Bold',
        fontSize=16 if not use_two_column else 14,
        alignment=TA_CENTER if not use_two_column else 0,
        spaceAfter=4
    )

    contact_style = ParagraphStyle(
        'Contact',
        fontName='Times-Roman',
        fontSize=10 if not use_two_column else 8,
        alignment=TA_CENTER if not use_two_column else 0,
        spaceAfter=12
    )

    header_style = ParagraphStyle(
        'Header',
        fontName='Times-Bold',
        fontSize=12 if not use_two_column else 10,
        spaceAfter=6,
        spaceBefore=12,
        borderWidth=1,
        borderColor=colors.black,
        borderPadding=4,
    )

    body_style = ParagraphStyle(
        'Body',
        fontName='Times-Roman',
        fontSize=11 if not use_two_column else 9,
        leading=14 if not use_two_column else 12
    )

    # SECTION SHUFFLING: Randomize order of main sections
    sections_order = ['education', 'experience', 'skills']
    random.shuffle(sections_order)

    # Build content sections
    education_content = []
    experience_content = []
    skills_content = []

    # Name & Contact
    story.append(Paragraph(name.upper(), name_style))
    contact_info = f"{email} • {phone} • {location}<br/>LinkedIn: {linkedin}"
    story.append(Paragraph(contact_info, contact_style))
    story.append(Spacer(1, 12))

    # EDUCATION SECTION
    education_content.append(Paragraph(headers['education'], header_style))

    if has_masters:
        master_dates = random_date_range(2, 4)
        edu_text = f"""<b>{master_degree}</b>
        <br/>{master_uni}, {location.split(',')[1].strip()}
        <br/>Grade: {master_grade}
        <br/><i>{master_dates[0]} - {master_dates[1]}</i>"""
        education_content.append(Paragraph(edu_text, body_style))
        education_content.append(Spacer(1, 8))

    bachelor_dates = random_date_range(5, 9)
    bachelor_text = f"""<b>{bachelor_degree}</b>
    <br/>{bachelor_uni}, {location.split(',')[1].strip()}
    <br/>Grade: {bachelor_grade}
    <br/><i>{bachelor_dates[0]} - {bachelor_dates[1]}</i>"""
    education_content.append(Paragraph(bachelor_text, body_style))

    # EXPERIENCE SECTION
    experience_content.append(Paragraph(headers['experience'], header_style))

    localized_content = LOCALIZED_CONTENT[nationality]

    for i in range(num_positions):
        job_title = random.choice(localized_content['job_titles'])
        company = random.choice(config['companies'])

        if i == 0:
            dates = (random_date_range(0, 1)[0], 'Present')
        else:
            dates = random_date_range(i*2, i*2 + 2)

        bullets = generate_experience_bullets(nationality, random.randint(4, 6))
        bullets_html = '<br/>'.join([f"• {b}" for b in bullets])

        exp_text = f"""<b>{job_title}</b> | {company}, {location} | <i>{dates[0]} - {dates[1]}</i>
        <br/>{bullets_html}"""
        experience_content.append(Paragraph(exp_text, body_style))

        if i < num_positions - 1:
            experience_content.append(Spacer(1, 10))

    # SKILLS SECTION - Use graphical bars 50% of the time
    use_skill_bars = random.choice([True, False])

    skills_content.append(Paragraph(headers['skills'], header_style))

    if use_skill_bars:
        # Note: Skill bars require direct canvas drawing, so we'll use a workaround
        # We'll add a placeholder and note that actual bars would be drawn differently
        skills_text = "<b>Note:</b> Skills visualized as proficiency bars below"
        skills_content.append(Paragraph(skills_text, body_style))
        skills_content.append(Spacer(1, 8))
        # Add skill names as fallback
        skills_list = ", ".join([skill for skill, _ in skill_bars_data])
        skills_content.append(Paragraph(f"<b>Core Skills:</b> {skills_list}", body_style))
    else:
        # Traditional text list
        skills_text = f"""<b>Languages & Tools:</b> {', '.join(selected_skills)}
        <br/><b>Certifications:</b> {random.choice(['AWS Certified Solutions Architect', 'Google Cloud Professional', 'Azure Developer Associate'])}"""
        skills_content.append(Paragraph(skills_text, body_style))

    # Add sections in randomized order
    section_map = {
        'education': education_content,
        'experience': experience_content,
        'skills': skills_content
    }

    for section_name in sections_order:
        story.extend(section_map[section_name])
        story.append(Spacer(1, 10))

    # For two-column: add FrameBreak between sidebar and main content
    if use_two_column:
        # In two-column, put skills in left sidebar, exp+edu in right
        story_left = []
        story_right = []

        # Sidebar: Name, Contact, Skills
        story_left.append(Paragraph(name.upper(), name_style))
        story_left.append(Paragraph(contact_info, contact_style))
        story_left.append(Spacer(1, 12))
        story_left.extend(skills_content)

        # Main: Experience and Education (in random order)
        remaining = [s for s in sections_order if s != 'skills']
        for section_name in remaining:
            story_right.extend(section_map[section_name])
            story_right.append(Spacer(1, 10))

        # Combine with FrameBreak
        story = story_left + [FrameBreak()] + story_right

    # Build PDF
    doc.build(story)
    
    return {
        'filename': filename,
        'name': name,
        'nationality': nationality,
        'flag': config['flag'],
        'visa_target': random.choice(config['visa_targets']),
        'age': age
    }

def main():
    print("\n" + "="*70)
    print("  GLOBAL ATS BRIDGE - Random CV Generator")
    print("="*70 + "\n")
    
    # Get user input
    try:
        num_cvs = int(input("How many CVs do you want to generate? (1-100): "))
        if num_cvs < 1 or num_cvs > 100:
            print("Please enter a number between 1 and 100")
            return
    except ValueError:
        print("Invalid input. Please enter a number.")
        return
    
    print("\nAvailable nationalities:")
    for i, (key, config) in enumerate(COUNTRY_CONFIGS.items(), 1):
        print(f"  {i}. {config['flag']} {key.title()}")
    
    print(f"  {len(COUNTRY_CONFIGS) + 1}. Random mix (all nationalities)")
    
    try:
        choice = int(input(f"\nSelect nationality (1-{len(COUNTRY_CONFIGS) + 1}): "))
        
        if choice == len(COUNTRY_CONFIGS) + 1:
            # Random mix
            nationalities = list(COUNTRY_CONFIGS.keys())
            selected_nationality = None
        elif 1 <= choice <= len(COUNTRY_CONFIGS):
            selected_nationality = list(COUNTRY_CONFIGS.keys())[choice - 1]
            nationalities = [selected_nationality]
        else:
            print("Invalid choice")
            return
    except ValueError:
        print("Invalid input. Please enter a number.")
        return
    
    print(f"\n{'='*70}")
    print(f"Generating {num_cvs} CV(s)...")
    print(f"{'='*70}\n")
    
    generated = []
    for i in range(num_cvs):
        nationality = random.choice(nationalities) if selected_nationality is None else selected_nationality
        result = generate_random_cv(nationality)
        generated.append(result)
        print(f"✓ Generated ({i+1}/{num_cvs}): {result['flag']} {result['name']} - {result['nationality'].title()}")
    
    print(f"\n{'='*70}")
    print(f"✓ SUCCESS: {num_cvs} CV(s) generated in 'test_cvs/' folder")
    print(f"{'='*70}\n")
    
    # Summary
    print("Summary:")
    nationality_counts = {}
    for cv in generated:
        nat = cv['nationality']
        nationality_counts[nat] = nationality_counts.get(nat, 0) + 1
    
    for nat, count in nationality_counts.items():
        flag = COUNTRY_CONFIGS[nat]['flag']
        print(f"  {flag} {nat.title()}: {count} CV(s)")
    
    print("\nAll CVs are ready for testing your ATS Bridge app!")
    print("Each CV has unique:")
    print("  • Names, emails, and phone numbers")
    print("  • Education backgrounds and grades")
    print("  • Work experience and achievements")
    print("  • Technical skills and certifications")

if __name__ == "__main__":
    main()