"""Pool of mock passenger names for seed data."""

import random
import string

NAMES = [
    # German
    "Elena Richter", "Sarah Hoffmann", "Lukas Weber", "Anna Muller", "Felix Braun",
    "Marie Schneider", "Tobias Wagner", "Lena Fischer", "Max Becker", "Julia Wolf",
    "Moritz Schulz", "Hannah Bauer", "Stefan Hartmann", "Lisa Kruger", "David Koch",
    "Katharina Lang", "Andreas Schwarz", "Sophie Zimmermann", "Christian Lehmann",
    "Claudia Schmitt",
    # French
    "Marco Bianchi", "Pierre Dubois", "Amelie Laurent", "Jean-Luc Martin", "Isabelle Bernard",
    "Francois Petit", "Camille Leroy", "Thierry Moreau", "Nathalie Simon", "Antoine Roux",
    "Margot Fournier", "Benoit Girard", "Celine Bonnet", "Yves Durand", "Virginie Dupont",
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
    "Carlos Garcia", "Maria Lopez", "Alejandro Martinez", "Lucia Hernandez", "Pablo Rodriguez",
    # Turkish
    "Elif Yilmaz", "Mehmet Demir", "Zeynep Celik", "Emre Sahin", "Ayse Kaya",
    # Scandinavian
    "Erik Lindgren", "Astrid Johansson", "Lars Eriksson", "Freya Nielsen", "Magnus Andersen",
    # Italian
    "Giulia Rossi", "Alessandro Romano", "Chiara Conti", "Matteo Ferrari", "Valentina Ricci",
    # African
    "Amara Diallo", "Kwame Asante", "Fatima Mbeki", "Chidi Okafor", "Zara Hassan",
    # Middle Eastern
    "Omar Al-Rashid", "Layla Khalil", "Hassan Aziz", "Noor Abbas", "Tariq Mansour",
    # Polish
    "Katarzyna Nowak", "Piotr Kowalski", "Agnieszka Wisniewska", "Tomasz Zielinski",
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
    "Markus Winter", "Tanja Schroeder", "Frank Neumann", "Anja Werner",
    "Joerg Haas", "Michaela Fuchs", "Ralf Grimm", "Heike Lorenz",
    "Andre Becker", "Ute Kaiser", "Dirk Richter", "Karin Albrecht",
    "Holger Baumann", "Martina Ludwig", "Klaus Brandt", "Silke Kraft",
    "Uwe Zimmermann", "Doris Stein", "Bernd Hahn", "Gabriele Pohl",
    "Volker Kraus", "Renate Vogel", "Helmut Friedrich", "Ursula Krug",
    "Juergen Schulte", "Ingrid Boehm", "Manfred Otto", "Angelika Horn",
    # Greek
    "Nikolaos Papadopoulos", "Eleni Georgiou", "Konstantinos Alexiou", "Sofia Dimitriou",
    # Czech
    "Jakub Novak", "Tereza Dvorakova", "Ondrej Svoboda", "Karolina Cerna",
    # Hungarian
    "Balazs Nagy", "Eszter Toth", "Gabor Kovacs", "Anna Szabo",
    # Portuguese
    "Joao Pereira", "Ines Rodrigues", "Miguel Fernandes", "Ana Carvalho",
    # Irish
    "Ciaran Murphy", "Siobhan Kelly", "Declan Byrne", "Aoife Walsh",
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


# --- Priority score calculation ---

_LOYALTY_BONUS = {"hon": 40, "sen": 25, "ftl": 10, "none": 0}
_BOOKING_CLASS_BONUS = {
    # First
    "F": 30, "A": 30,
    # Business
    "J": 20, "C": 20, "D": 20, "Z": 20,
    # Premium Economy
    "E": 10, "N": 10, "P": 10,
    # Economy full-fare
    "Y": 5, "B": 5,
    # Economy discounted — no bonus
}


def compute_priority(loyalty_tier: str, booking_class: str) -> int:
    """Compute passenger priority score from loyalty tier and booking class."""
    return _LOYALTY_BONUS.get(loyalty_tier, 0) + _BOOKING_CLASS_BONUS.get(booking_class, 0)


# --- Profile distribution ---

def default_distribution(n: int, rng: random.Random | None = None) -> list[tuple[str, str]]:
    """Generate a realistic LH flight passenger profile distribution.

    Returns list of (loyalty_tier, booking_class) tuples.
    """
    r = rng or random.Random()
    profiles: list[tuple[str, str]] = []

    # HON Circle (~1-2%)
    hon_count = max(1, round(n * 0.02))
    profiles.extend([("hon", r.choice(["J", "C"])) for _ in range(hon_count)])

    # Senator (~5%)
    sen_count = max(2, round(n * 0.05))
    profiles.extend([("sen", r.choice(["C", "D", "Y"])) for _ in range(sen_count)])

    # Frequent Traveller (~15%)
    ftl_count = max(3, round(n * 0.15))
    profiles.extend([("ftl", r.choice(["Z", "Y", "B", "H"])) for _ in range(ftl_count)])

    # No status — rest
    none_count = n - len(profiles)
    eco_discount = ["M", "L", "T", "V", "W", "Q"]
    eco_full = ["Y", "B"]
    # ~15% of no-status get full-fare economy, rest discounted
    full_fare_count = max(1, round(none_count * 0.15))
    profiles.extend([("none", r.choice(eco_full)) for _ in range(full_fare_count)])
    profiles.extend([("none", r.choice(eco_discount)) for _ in range(none_count - full_fare_count)])

    r.shuffle(profiles)
    return profiles


def make_booking_ref(rng: random.Random | None = None) -> str:
    r = rng or random.Random()
    return "".join(r.choices(string.ascii_uppercase + string.digits, k=6))


def pick_passengers(
    n: int,
    start_index: int = 0,
    profile_distribution: list[tuple[str, str]] | None = None,
    rng: random.Random | None = None,
) -> list[tuple[str, str, str, str, str]]:
    """Return n (id, name, booking_ref, loyalty_tier, booking_class) tuples.

    If profile_distribution is None, generates a realistic default distribution.
    """
    if profile_distribution is None:
        profile_distribution = default_distribution(n, rng=rng)

    # Ensure distribution matches requested count
    if len(profile_distribution) < n:
        r = rng or random.Random()
        extra = n - len(profile_distribution)
        profile_distribution = list(profile_distribution) + [
            ("none", r.choice(["M", "L", "T", "V", "W", "Q"])) for _ in range(extra)
        ]

    result = []
    for i in range(n):
        idx = (start_index + i) % len(NAMES)
        pid = f"pax-{start_index + i + 1:03d}"
        loyalty_tier, booking_class = profile_distribution[i]
        result.append((pid, NAMES[idx], make_booking_ref(rng), loyalty_tier, booking_class))
    return result
