# Listening Notes working agreement

Read `AGENTS.md` before starting work; it is the durable project guide for both
editorial and technical rules.

This project follows the universal two-machine ritual:

- MacBook is the control terminal and light-editing surface at
  `/Users/israel/Code/ior-listening-notes`.
- Mac Pro is the primary execution host at
  `/Users/Israel/Code/ior-listening-notes`, accessed with `ssh MacPro`.
- GitHub `main` is the cross-machine authority.

At session start, check both worktrees for dirty or divergent state. Before
publishing, run the relevant validation on MacPro. After publishing,
fast-forward MacPro and confirm both worktrees are clean. Use
`scripts/remote_run_macpro.sh` for repository commands.
