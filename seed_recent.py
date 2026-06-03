"""
Builds recent_2026.csv - the set of current (2026) examples that get folded into the
model by update_model.py. The base Kaggle data stops around 2017, so without this the
model has never seen recent names, topics or vocabulary.

REAL (label 0): neutral, wire-service-style writing about plausible 2026 events.
FAKE (label 1): clickbait / conspiracy / scam-style writing on the same kinds of topics.

There's a handful of hand-written examples plus a generator that mixes building blocks
so we get a few hundred varied rows instead of the same sentence over and over. Re-run
this any time you want to refresh or grow the set, then run update_model.py.
"""
import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "recent_2026.csv")
random.seed(2026)  # fixed seed so the file is reproducible

# ---------------------------------------------------------------- hand-written REAL
REAL_CORE = [
    "Russian forces launched a large overnight aerial attack on Kyiv and other Ukrainian cities, with local officials reporting at least 22 civilians killed and more than 130 wounded. Emergency crews worked through the morning to clear rubble and restore power to several districts.",
    "Iran said on Tuesday it would pause negotiations with the United States and warned it could move to block shipping through the Strait of Hormuz. Analysts noted that any disruption to the waterway, which carries a large share of the world's oil, could push energy prices higher.",
    "The United States embassy in Beirut confirmed that Hezbollah had accepted a proposal for a mutual cessation of attacks with Israel. Officials said the Lebanese government received written confirmation of the arrangement, which is meant to ease fighting along the southern border.",
    "The European Union advanced an overhaul of its migration policy this week, moving ahead with measures that would increase deportations and set up processing centres outside the bloc. Member states are expected to debate the details before the rules take effect.",
    "Tens of thousands of ultra-Orthodox Israelis protested across the country on Monday against mandatory military enlistment, blocking roads and rail lines. Police said major routes were reopened by the evening as demonstrations continued in several cities.",
    "Tough-on-crime candidate Abelardo de la Espriella took an early lead in Colombia's presidential race, according to preliminary results, setting up a likely runoff with senator Ivan Cepeda. Electoral authorities said certified figures would follow in the coming days.",
    "Russia's crude oil exports reached their highest level since before the 2022 invasion of Ukraine, according to shipping data reviewed this month. The rise coincided with higher global oil prices linked to tensions in the Middle East.",
    "The Federal Reserve held its benchmark interest rate steady on Wednesday and signalled patience before any further move, citing mixed labour-market data and slowly easing inflation. The chair told reporters policymakers wanted to see more figures first.",
    "Delegates at a United Nations climate session reviewed progress on emissions targets this week, with several governments presenting updated national plans. Negotiators said disagreements remained over financing for developing countries ahead of the next summit.",
    "A magnitude 6.1 earthquake struck a coastal region early on Sunday, prompting brief evacuations and minor damage to older buildings, according to the national seismological agency. No deaths were reported, though aftershocks were expected.",
    "Lawmakers approved a budget measure on Thursday after a long debate, setting aside money for transport projects and public services for the coming year. The bill now moves to the upper chamber, where further amendments are likely.",
    "A regulator opened a review of a large technology company's data-sharing practices following complaints from consumer groups. The company said it would cooperate fully and defended its handling of user information in a written statement.",
    "Health authorities reported that a seasonal vaccination campaign had reached most of its target age groups, citing figures from the regional health department. Clinics said demand stayed steady through the spring as the programme wound down.",
    "Officials confirmed the new high-speed rail line would open to passengers next month after final safety testing. The project, delayed twice by funding gaps, is expected to cut travel time between the two cities by roughly half.",
    "The central bank of a major economy left rates unchanged but trimmed its growth forecast for the year, citing weaker exports and softer consumer spending. Markets were little changed after the announcement.",
]

# ---------------------------------------------------------------- hand-written FAKE
FAKE_CORE = [
    "SHOCKING leak proves the war was secretly staged by global elites to crash the economy, and THEY don't want you to know the truth. Share this before it gets deleted forever because the mainstream media is being PAID to hide what really happened.",
    "BREAKING they are HIDING it from you: a miracle free-energy device that makes oil obsolete was just revealed, and Big Oil is FURIOUS. Insiders are being silenced, so click now before this video is BANNED and wiped from the internet.",
    "EXPOSED: the so-called ceasefire is a HOAX and the real plan is a secret one-world government takeover set for 2026. Wake up, sheeple, the proof THEY tried to bury is finally out and you won't believe number 7.",
    "Doctors are FURIOUS after a man cured every disease overnight using one weird kitchen trick the pharma cartel has suppressed for decades. The cure THEY don't want you to have is being deleted everywhere, so share it immediately.",
    "URGENT: the new migration law secretly installs mind-control chips through the water supply, according to a whistleblower THEY tried to silence. Forward this to everyone you love right now before the truth is scrubbed from the web.",
    "You won't BELIEVE what scientists found: the earthquake was actually a secret weapon test and the government is covering it up with fake news. The footage THEY banned just leaked, click before it vanishes forever.",
    "MIRACLE breakthrough: this common fruit melts belly fat overnight and doctors HATE it because it destroys their billion-dollar industry. The recipe big corporations tried to ban is finally exposed, share before it's gone.",
    "ALERT the election was RIGGED by a secret algorithm and insiders are leaking the proof THEY don't want public. The media is being PAID to ignore it, so spread this everywhere before your account is shadow-banned.",
    "BOMBSHELL the climate summit is a front for elites to seize your money and freedom, according to a leaked document. Wake up before it's too late, this is the truth THEY have hidden from you for years.",
    "They FINALLY admitted it: the vaccine campaign is a secret population experiment and a brave insider just exposed everything. Share this truth immediately before the censors delete it because the powerful don't want you to know.",
    "SECRET government file proves oil prices are rigged by a hidden cabal to enslave the working class, and they're terrified you'll find out. Click here for the banned report before it's wiped from every server tonight.",
    "INSANE this one trick makes you rich overnight and banks are DESPERATE to hide it from ordinary people. The elite tried to ban this video a thousand times, watch and share before it disappears.",
    "WARNING 5G towers installed this year are secretly controlling the weather and they're lying to your face about it. The whistleblower who exposed it has gone missing, share before they erase this completely.",
    "They don't want you to see this: a celebrity revealed the shocking secret behind the new currency and was instantly silenced by the powerful people who run everything from the shadows.",
    "MUST SEE before deleted: aliens have been advising world leaders since 2026 and the proof is finally leaking out despite a massive cover-up. Click now, this changes absolutely everything you thought you knew.",
]

# ---------------------------------------------------------------- REAL generator parts
ACTORS = [
    "The government", "Officials", "The central bank", "Lawmakers", "A regulator",
    "The health ministry", "The defence ministry", "Election officials", "The prime minister",
    "The president", "A parliamentary committee", "The trade ministry", "The interior ministry",
    "The national weather service", "The transport authority", "The finance ministry",
]
EVENTS = [
    "announced new measures to ease inflation",
    "approved funding for a major transport project",
    "reported a steady drop in unemployment over the quarter",
    "signed a trade agreement with a neighbouring country",
    "launched an inquiry into the recent data breach",
    "confirmed the timeline for the upcoming election",
    "set out a plan to expand renewable energy capacity",
    "issued a flood warning for low-lying coastal areas",
    "outlined reforms to the public health system",
    "agreed to extend the existing ceasefire by another month",
    "presented the annual budget to parliament",
    "imposed new limits on certain imports",
    "opened a review of housing affordability rules",
    "reported progress in talks over the disputed border",
    "unveiled a relief package for areas hit by drought",
    "raised the minimum wage for the coming year",
]
ATTR = [
    "according to a statement released on Tuesday.",
    "officials said at a news conference on Wednesday.",
    "the agency confirmed in a written notice.",
    "according to figures published this week.",
    "a spokesperson told reporters on Thursday.",
    "according to documents seen by local media.",
    "the ministry said in an official release.",
    "according to preliminary data reviewed on Friday.",
]
FOLLOW = [
    "Analysts said the move was broadly in line with expectations.",
    "The opposition called for further details before giving its support.",
    "Several economists welcomed the decision while urging caution.",
    "Markets reacted modestly to the news.",
    "Critics argued the plan did not go far enough.",
    "The measure is expected to take effect later this year.",
    "Further talks are scheduled in the coming weeks.",
    "Community groups said they would monitor how the rules are applied.",
]

# ---------------------------------------------------------------- FAKE generator parts
HOOKS = [
    "SHOCKING", "BREAKING", "URGENT", "EXPOSED", "BOMBSHELL", "ALERT", "MUST SEE",
    "THEY LIED", "WAKE UP", "LEAKED", "BANNED VIDEO", "INSANE",
]
CLAIMS = [
    "a secret cabal is rigging prices to control the population",
    "this one weird trick cures every disease overnight and doctors hate it",
    "the government is hiding aliens who advise world leaders",
    "a miracle pill melts fat instantly while you sleep",
    "5G towers are secretly controlling your mind and the weather",
    "the election was stolen by a hidden algorithm nobody is allowed to mention",
    "vaccines contain microchips that track your every move",
    "elites are planning a one-world takeover this year",
    "free unlimited energy exists but big corporations buried it",
    "this stock will make you a millionaire overnight, guaranteed",
    "the news you watch is scripted by the same twelve families",
    "a banned remedy reverses aging in just three days",
]
CTAS = [
    "Share this before it gets DELETED forever!",
    "Click now before THEY ban it!",
    "Forward to everyone you love before it's too late!",
    "Watch before this is scrubbed from the internet!",
    "Spread the truth before your account is shadow-banned!",
    "Do this NOW, you won't believe what happens next!",
    "The powerful don't want you to see this, hurry!",
    "Save this post before it vanishes tonight!",
]
WHY = [
    "The mainstream media is PAID to keep you in the dark.",
    "Insiders who spoke out have already gone missing.",
    "This is the truth THEY have hidden for years.",
    "Wake up before it is too late.",
    "Number 7 will leave you speechless.",
    "Big corporations have tried to bury this a thousand times.",
]


def gen_real(n):
    out = []
    for _ in range(n):
        s = f"{random.choice(ACTORS)} {random.choice(EVENTS)}, {random.choice(ATTR)} {random.choice(FOLLOW)}"
        out.append(s)
    return out


def gen_fake(n):
    out = []
    for _ in range(n):
        s = (
            f"{random.choice(HOOKS)}: {random.choice(CLAIMS)} and they don't want you to know. "
            f"{random.choice(WHY)} {random.choice(CTAS)}"
        )
        out.append(s)
    return out


def dedupe(seq):
    seen, out = set(), []
    for s in seq:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def main():
    real = dedupe(REAL_CORE + gen_real(140))
    fake = dedupe(FAKE_CORE + gen_fake(140))
    # balance the two classes
    n = min(len(real), len(fake))
    real, fake = real[:n], fake[:n]

    rows = [(t, 0) for t in real] + [(t, 1) for t in fake]
    random.shuffle(rows)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["text", "label"])
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows ({len(real)} real, {len(fake)} fake) -> {OUT}")


if __name__ == "__main__":
    main()
