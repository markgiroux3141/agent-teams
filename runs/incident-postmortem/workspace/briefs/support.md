# Support brief — incident 2026-04-20

## What I have

Ticket queue for the incident window (14:00–15:00 UTC). 47 tickets
opened, 2 closed in-window, rest still open.

## Dominant pattern (38 of 47 tickets)

Users report being **logged in successfully, then getting kicked
out partway through checkout**. Many describe having to re-login
multiple times to complete a purchase.

Representative quotes (verbatim):

> "I logged in fine, added items to my cart, clicked checkout, and
> it told me my session expired. I logged back in and tried again.
> It worked for a couple of minutes and then kicked me out again."
> — ticket #18422

> "Got logged out mid-checkout THREE times before it let me pay."
> — ticket #18431

> "I was logged in, went to add a coupon, got an error saying I
> was signed out. Signed in, tried again, was fine for about 5
> minutes, then got signed out again."
> — ticket #18444

> "This has never happened to me before. I don't think it's my
> wifi. I was on my phone too and had the same thing happen."
> — ticket #18409

> "Kept getting 'session expired' even though I hadn't even closed
> the tab. I was still in the middle of typing my card number."
> — ticket #18461

**Pattern timing cue:** Multiple tickets mention sessions lasting
"a few minutes" after re-login before dying again. This is specific
and unusual — normal session-expired errors happen after hours of
idle, not minutes.

## Secondary patterns

- 6 tickets about the site "being slow today" — no specific error.
  These do not cite session or checkout issues. Likely unrelated
  background noise or incidental.
- 3 tickets about coupon codes not applying. These are ambiguous —
  might be incident-related (failed mid-checkout), might be normal
  coupon gripes.

## My initial read

The dominant pattern is unambiguous: **session lifetime shortened
from what users expect to ~minutes**. Users were not just getting
random errors — their sessions were being cut short in a way that
felt "wrong" to the people experiencing it. Several users
explicitly noticed the short lifetime and said so.

This doesn't look like auth system failure (which would deny login).
Users successfully log in. Something about established sessions is
going wrong shortly after.

## What I don't know

- Why established sessions are dying so quickly.
- Whether anything specific about the affected users (platform,
  region, session age) would narrow this down — the ticket set is
  too small to segment meaningfully.
