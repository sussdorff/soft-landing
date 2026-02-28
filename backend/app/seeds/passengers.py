"""Pool of mock passenger names for seed data."""

import random
import string

NAMES = [
    # German
    "Elena Richter", "Sarah Hoffmann", "Lukas Weber", "Anna Müller", "Felix Braun",
    "Marie Schneider", "Tobias Wagner", "Lena Fischer", "Max Becker", "Julia Wolf",
    "Moritz Schulz", "Hannah Bauer", "Stefan Hartmann", "Lisa Krüger", "David Koch",
    "Katharina Lang", "Andreas Schwarz", "Sophie Zimmermann", "Christian Lehmann",
    "Claudia Schmitt",
    # French
    "Marco Bianchi", "Pierre Dubois", "Amélie Laurent", "Jean-Luc Martin", "Isabelle Bernard",
    "François Petit", "Camille Leroy", "Thierry Moreau", "Nathalie Simon", "Antoine Roux",
    "Margot Fournier", "Benoît Girard", "Céline Bonnet", "Yves Durand", "Virginie Dupont",
    # Japanese
    "Yuki Tanaka", "Haruto Suzuki", "Sakura Yamamoto", "Kenji Watanabe", "Aiko Nakamura",
    "Takeshi Ito", "Mika Sato", "Ryo Kobayashi", "Yuna Kato", "Daisuke Yoshida",
    # American / English
    "James O'Connor", "Emily Johnson", "Michael Davis", "Jessica Wilson", "Robert Miller",
    "Jennifer Brown", "William Anderson", "Amanda Taylor", "Christopher Thomas", "Stephanie Lee",
    "Daniel Moore", "Nicole Clark", "Matthew White", "Samantha Harris", "Joshua Martin",
    # Indian
    "Priya Sharma", "Arjun Patel", "Neha Gupta", "Rahul Singh", "Ananya Reddy",
    "Vikram Joshi", "Pooja Kumar", "Siddharth Das", "Meera Nair", "Rohan Mehta",
    # Korean
    "Jiyeon Kim", "Minho Park", "Soojin Lee", "Hyunwoo Choi", "Eunji Jung",
    # Brazilian
    "Lucas Silva", "Beatriz Santos", "Rafael Oliveira", "Camila Costa", "Thiago Ferreira",
    # Spanish
    "Carlos García", "María López", "Alejandro Martínez", "Lucía Hernández", "Pablo Rodríguez",
    # Turkish
    "Elif Yılmaz", "Mehmet Demir", "Zeynep Çelik", "Emre Şahin", "Ayşe Kaya",
    # Scandinavian
    "Erik Lindgren", "Astrid Johansson", "Lars Eriksson", "Freya Nielsen", "Magnus Andersen",
    # Italian
    "Giulia Rossi", "Alessandro Romano", "Chiara Conti", "Matteo Ferrari", "Valentina Ricci",
    # African
    "Amara Diallo", "Kwame Asante", "Fatima Mbeki", "Chidi Okafor", "Zara Hassan",
    # Middle Eastern
    "Omar Al-Rashid", "Layla Khalil", "Hassan Aziz", "Noor Abbas", "Tariq Mansour",
    # Polish
    "Katarzyna Nowak", "Piotr Kowalski", "Agnieszka Wiśniewska", "Tomasz Zieliński",
    # Dutch
    "Daan de Vries", "Sophie van den Berg", "Bram Jansen", "Emma Bakker",
    # Chinese
    "Wei Zhang", "Mei Lin Chen", "Jun Li Wang", "Xiao Liu", "Hao Yang",
    # Russian
    "Natalia Ivanova", "Dmitri Petrov", "Olga Smirnova", "Alexei Volkov",
    # Additional names
    "Thomas Krause", "Monika Keller", "Patrick Engel", "Susanne Vogt",
    "Oliver Winkler", "Nina Bergmann", "Florian Roth", "Petra Lange",
    "Martin Huber", "Sandra Frank", "Jan Scholz", "Birgit Sommer",
    "Markus Winter", "Tanja Schröder", "Frank Neumann", "Anja Werner",
    "Jörg Haas", "Michaela Fuchs", "Ralf Grimm", "Heike Lorenz",
    "André Becker", "Ute Kaiser", "Dirk Richter", "Karin Albrecht",
    "Holger Baumann", "Martina Ludwig", "Klaus Brandt", "Silke Kraft",
    "Uwe Zimmermann", "Doris Stein", "Bernd Hahn", "Gabriele Pohl",
    "Volker Kraus", "Renate Vogel", "Helmut Friedrich", "Ursula Krug",
    "Jürgen Schulte", "Ingrid Böhm", "Manfred Otto", "Angelika Horn",
    # Greek
    "Nikolaos Papadopoulos", "Eleni Georgiou", "Konstantinos Alexiou", "Sofia Dimitriou",
    # Czech
    "Jakub Novák", "Tereza Dvořáková", "Ondřej Svoboda", "Karolína Černá",
    # Hungarian
    "Balázs Nagy", "Eszter Tóth", "Gábor Kovács", "Anna Szabó",
    # Portuguese
    "João Pereira", "Inês Rodrigues", "Miguel Fernandes", "Ana Carvalho",
    # Irish
    "Ciarán Murphy", "Siobhán Kelly", "Declan Byrne", "Aoife Walsh",
    # Thai
    "Somchai Thongdee", "Nattaya Srisawat", "Kittipong Chaiyasit", "Pimchanok Rattanakul",
    # Filipino
    "Miguel Santos", "Maria Cruz", "Jose Reyes", "Angela Mendoza",
    # Austrian
    "Florian Gruber", "Katharina Steiner", "Lukas Pichler", "Elisabeth Hofer",
    # Swiss
    "Luca Brunner", "Noemi Meier", "Yannik Schmid", "Lea Keller",
]

assert len(NAMES) >= 150, f"Need 150+ names, got {len(NAMES)}"


def make_booking_ref() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def pick_passengers(n: int, start_index: int = 0) -> list[tuple[str, str, str]]:
    """Return n (id, name, booking_ref) tuples starting from start_index."""
    result = []
    for i in range(n):
        idx = (start_index + i) % len(NAMES)
        pid = f"pax-{start_index + i + 1:03d}"
        result.append((pid, NAMES[idx], make_booking_ref()))
    return result
