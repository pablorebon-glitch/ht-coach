# HT Coach Architecture

## Vision

HT Coach is not a Hattrick calculator.

HT Coach is a football assistant that recommends the best lineup,
individual orders and tactical decisions based on mathematical models.

---

## Pipeline

Player
    ↓
Position Engine
    ↓
Contribution
    ↓
Team Calculator
    ↓
Team Ratings
    ↓
Match Analyzer
    ↓
Recommendation Engine

---

## Principles

- Every module has one responsibility.
- Position engines calculate contributions.
- Team calculator sums contributions.
- Match analyzer compares ratings.
- Recommendation engine suggests changes.
