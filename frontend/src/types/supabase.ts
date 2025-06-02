export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      messages: {
        Row: {
          id: string;
          contact_id: string;
          sender: string | null;
          channel: string | null;
          content: string | null;
          status: string | null;
          metadata: Json | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          contact_id: string;
          sender?: string | null;
          channel?: string | null;
          content?: string | null;
          status?: string | null;
          metadata?: Json | null;
          created_at?: string;
        };
        Update: {
          id?: string;
          contact_id?: string;
          sender?: string | null;
          channel?: string | null;
          content?: string | null;
          status?: string | null;
          metadata?: Json | null;
          created_at?: string;
        };
      };
      contacts: {
        Row: {
          id: string;
          name: string | null;
          email: string | null;
          telegram_id: string | null;
          created_at: string;
          updated_at: string;
          first_name: string | null;
          last_name: string | null;
          username: string | null;
          language_code: string | null;
        };
        Insert: {
          id?: string;
          name?: string | null;
          email?: string | null;
          telegram_id?: string | null;
          created_at?: string;
          updated_at?: string;
          first_name?: string | null;
          last_name?: string | null;
          username?: string | null;
          language_code?: string | null;
        };
        Update: {
          id?: string;
          name?: string | null;
          email?: string | null;
          telegram_id?: string | null;
          created_at?: string;
          updated_at?: string;
          first_name?: string | null;
          last_name?: string | null;
          username?: string | null;
          language_code?: string | null;
        };
      };
      user_details: {
        Row: {
          id: string;
          user_id: string;
          working_hours_start: string | null;
          working_hours_end: string | null;
          meeting_duration: number | null;
          buffer_time: number | null;
          telegram_id: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          working_hours_start?: string | null;
          working_hours_end?: string | null;
          meeting_duration?: number | null;
          buffer_time?: number | null;
          telegram_id?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          user_id?: string;
          working_hours_start?: string | null;
          working_hours_end?: string | null;
          meeting_duration?: number | null;
          buffer_time?: number | null;
          telegram_id?: string | null;
          created_at?: string;
          updated_at?: string;
        };
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      [_ in never]: never;
    };
    Enums: {
      [_ in never]: never;
    };
  };
} 