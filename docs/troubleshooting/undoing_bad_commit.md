# Undoing a bad commit

To roll back a commit (or revert a particular file), we can use `git checkout`:

1. Check out the working branch

2. List the commit messages

   ```sh
   # show commit history for current branch
   git log
   #  commit c4aad196a294db5e2d01a63c549e50bcc6f1f7ac (HEAD -releases/0.0.1, origin/releases/0.0.1)
   # Author: Alex Graber <alex.graber@pmi.org>
   # Date:   Thu Sep 29 10:33:02 2022 -0400
   #   this is a commit message
   ```

3. Identify the `<commit_hash>` _prior_ to the commit where the changed happened
   (we want the file as of the prior state, not as of the updated state)

4. Show the diffs between current and prior commit

   ```sh
   # show the difference between current and specified prior commit
   git diff <commit-hash> </path/to/file/to/revert>
   ```

5. Revert file to commit hash

   ```sh
   # refert specified file to specified prior commit
   git checkout <commit-hash> -- </path/to/file/to/revert>
   ```
