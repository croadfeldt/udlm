# Security policy

UDLM is a specification: schemas, a class registry, worked examples and the gates that check them.
It ships no running service. A security problem here is one of these:

- a rule or schema that lets an implementation leak, forge or lose data while still conforming;
- a worked example or test fixture that carries a real credential, key, address or private value;
- a gate that can be bypassed so a refused record passes CI.

## Reporting

Report privately to the maintainers listed in `MAINTAINERS.md` through GitHub's private
vulnerability reporting on this repository. Do not open a public issue for a problem that affects
implementations in use.

You will get an acknowledgement within 5 working days and a decision within 30 days: a fix, a
register row that narrows the rule, or a reason the report is not a security problem.

## Disclosure

A fix lands as a pull request that names the problem plainly once it is merged. Implementations
are told through the register row and the release notes; a peer that pins a UDLM commit decides
when to move.
