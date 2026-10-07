# ISNET CMS Authentication

1. Create a Supabase project.
2. Run `schema.sql` in the Supabase SQL editor.
3. Create the first user in Supabase Authentication.
4. Insert that user's UUID into `public.profiles` with role `super_admin`.
5. Copy `config.example.js` to `config.js`.
6. Put the project's public URL and public anon key in `config.js`, then set `enabled: true`.
7. Never expose the Supabase service_role key in browser code.

Until step 6 is complete, existing admin pages remain in pilot mode so the current CMS is not accidentally locked.
