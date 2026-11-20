# Investco: AI Assistant Prompt

## Project
Investco is an investment calculator. It helps users estimate how an investment grows over time.

## Goals
- Calculate future value from an initial amount, periodic contributions, an annual rate of return, and a time horizon.
- Support configurable compounding frequency (annual, monthly, daily).
- Show total contributions, total interest earned, and final balance.

## Guidelines
- Keep calculation logic in pure, exported functions, separate from any UI or I/O.
- Validate inputs (no negative amounts or periods; rates must be numbers) and return clear errors.
- Add focused tests for each calculation, including edge cases such as a 0% rate, 0 contributions, and fractional years.
- Keep the code simple and dependency-light, and document formulas in short comments only where they aren't obvious.

## When responding
- Be concise and show the formula used.
- Prefer small, surgical changes over large rewrites.
- Run the tests before declaring a change complete.
