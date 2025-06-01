# Database Setup Guide for Athena

## Current Issue

Your bot is working, but the database schema is missing some required columns. This causes errors like:

```
Could not find the 'first_name' column of 'contacts' in the schema cache
'SupabaseClient' object has no attribute 'get_contact_by_telegram_id'
```

## Quick Fix (Recommended)

### Option 1: Manual SQL Fix (Fastest)

1. **Go to your Supabase dashboard**:
   - Visit: https://app.supabase.com/
   - Select your project
   - Go to "SQL Editor"

2. **Run this SQL script**:
   ```sql
   -- Add missing columns to contacts table
   ALTER TABLE contacts 
   ADD COLUMN IF NOT EXISTS first_name TEXT,
   ADD COLUMN IF NOT EXISTS last_name TEXT,
   ADD COLUMN IF NOT EXISTS username TEXT,
   ADD COLUMN IF NOT EXISTS language_code TEXT,
   ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

   -- Create updated_at trigger
   CREATE OR REPLACE FUNCTION update_updated_at_column()
   RETURNS TRIGGER AS $$
   BEGIN
       NEW.updated_at = NOW();
       RETURN NEW;
   END;
   $$ language 'plpgsql';

   -- Add trigger to contacts table
   DROP TRIGGER IF EXISTS update_contacts_updated_at ON contacts;
   CREATE TRIGGER update_contacts_updated_at
       BEFORE UPDATE ON contacts
       FOR EACH ROW
       EXECUTE FUNCTION update_updated_at_column();
   ```

3. **Deploy your updated code** to Render (the code fixes are already committed)

4. **Test your bot** - Send `/start` to your bot on Telegram

### Option 2: Automated Script

If you have local access:

```bash
# Run the database setup script
python scripts/setup_database.py
```

## Verification

After running the SQL commands, your bot should:
- ✅ Receive messages without errors
- ✅ Create contacts successfully
- ✅ Store conversation history

Check your Render logs - you should see:
```
Successfully created contact for telegram_id 849748414
Message sent to 849748414: Hello! I'm Athena...
```

## Complete Database Schema

If you want to start fresh, you can also run the complete schema from `database/schema.sql`.

## Troubleshooting

### Error: "permission denied"
- Make sure you're using the **Service Role Key** in your `SUPABASE_SERVICE_ROLE_KEY` environment variable
- Check that RLS (Row Level Security) policies allow your operations

### Error: "table does not exist"
- Run the complete schema setup from `database/schema.sql`
- Ensure you're in the correct Supabase project

### Still getting contact creation errors?
- Check the Render logs for the specific error
- Verify your Supabase URL and keys are correct
- Make sure the `contacts` table exists and is accessible

## Next Steps

1. **Fix the database** (using Option 1 above)
2. **Deploy the updated code** 
3. **Test your bot** with `/start`
4. **Monitor logs** for successful message processing
5. **Continue with calendar integration** (Task 4.0 in your task list)

The webhook is now working correctly - we just need to fix the database schema! 