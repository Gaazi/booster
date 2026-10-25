# Verified compressed builds and demo promotion

## Automatic pipeline

Every push/merge to `dev`, `demo` or `main`, and every pull request targeting these
branch, runs `.github/workflows/build.yml`. It does not publish packages, deploy
a website, promote branches automatically or require publishing credentials.

1. Test core-only installation/regressions on Python 3.10; run the full server
   suite on 3.11 and 3.14, including Django privacy regressions. The current
   Starlette server dependency requires Python 3.11+, while core supports 3.10+.
   Full Python jobs explicitly select Node 24 for the cross-runtime journal test.
2. Install the locked development toolchain, compile canonical TypeScript and
   check generated public declarations; run native TS tests on Node 22 and 24.
3. Only after tests pass, build a Python wheel and source archive and use
   `npm pack --ignore-scripts` to build the Node archive.
4. Combine the three compressed distributions into `booster-COMMIT.zip` with
   a manifest containing the full commit SHA and SHA-256 package checksums.
5. Download the bundle, verify its inventory/commit/checksums, and smoke-test
   actual core-only wheel and optional standalone extras outside the checkout.
   Run the same native TypeScript regressions against the installed Node archive.

The final `Verified packages` job fails when an earlier required step fails;
an absent/skipped build is not accepted as success. Artifacts uploaded before
the installation check completes are candidates, not verified releases.
Wait for the entire `Verified build` run to succeed before using a download.

On a `demo` push of the **identical commit**, the pipeline can reuse an available
artifact from a successful `dev` push run in this repository. It still verifies
checksums and package installation. It never reuses PR/fork artifacts, other
workflow results, expired artifacts or a different commit's build. If no
eligible artifact exists, full tests and packaging run automatically.
A merge commit or conflict resolution changes the commit SHA and requires a
new build, even if much of its source looks similar.

Actions are pinned to full commit IDs. The workflow token has read-only content
and Actions access. Old in-progress runs on the same branch/event are cancelled.
Dependency downloads are cached; artifacts are retained for 30 days.
Dependencies still follow the project's declared version ranges; these builds
are identified/verified, not a promise of bit-for-bit reproducibility or zero bugs.

## One-command promotion after explicit authorization

Keep `demo` as a promotion branch; integrate changes on `dev`. Once its CI has
finished successfully, preview the exact build with:

```powershell
python -m scripts.promote_demo
```

When the user requests promotion for this occasion, run:

```powershell
python -m scripts.promote_demo --authorized --authorization-note "merge dev to demo"
```

The command requires Git, an authenticated GitHub CLI, the shared agent merge
helper, a clean `dev` checkout matching `origin/dev`, a successful dev
CI run, and a downloaded bundle with matching commit/checksums. It invokes the
shared merge helper with the user's actual instruction and immediately pushes
`demo`. It checks that the resulting tree equals the verified dev tree and that
the tested commit is an ancestor. The helper records authorization in a merge
commit, so GitHub builds and verifies that new demo commit. An identical SHA can
reuse an existing dev artifact as described above. No force push, automatic conflict
resolution, main merge or deployment is performed.
Preview only verifies/downloads the dev build. During an authorized promotion,
an outdated local `demo` catches up to `origin/demo` only by fast-forward fetch;
unpublished/diverged demo work and active worktree protections stop the command.

If `demo` has diverged, reconcile the changes on `dev` and verify its new CI
before retrying. If remote policies reject the push, the command fails visibly;
it never bypasses branch protection or discards the local merge.
This helper gates its own promotions. Enforcing required checks for **every**
GitHub/UI/direct push additionally needs repository branch protection/rulesets;
the workflow does not change those settings.

## Downloads and local verification

Open the successful run under GitHub Actions and download `booster-build-COMMIT`.
GitHub wraps the artifact in a ZIP; inside it is `booster-COMMIT.zip` containing
the wheel, source archive, Node `.tgz` and `manifest.json`. Install only the
package for the consumer's runtime. A wheel is already a compressed package.
To verify and unpack the inner bundle into a new directory:

```powershell
python -m scripts.build_bundle verify PATH_TO_BUNDLE.zip --sha FULL_COMMIT_SHA --extract-to build/verified-download
python -m pip install build/verified-download/booster-VERSION-py3-none-any.whl
# Optional standalone dashboard/server:
python -m pip install "build/verified-download/booster-VERSION-py3-none-any.whl[server]"
npm install ./build/verified-download/booster-node-VERSION.tgz
```

Checksums detect mismatches; trust comes from selecting a successful run in the
correct repository. Package compression is separate from HTTP GZip/Brotli:
browser responses still require proper negotiation and one compression owner.
