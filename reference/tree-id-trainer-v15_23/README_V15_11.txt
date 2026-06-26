TREE ID TRAINER v15.11

Android speech reliability fix:
- Reloads installed voices when the app regains focus
- Resumes Android speech after the app has been backgrounded
- Avoids cancel/speak in the same browser tick
- Keeps the current utterance alive until speech ends
- Falls back to the device default voice if a selected voice fails
- Test voice remains available while Android is still loading its voice list

Includes all v15.10 visual fixes and global/local counter code.
