import { useEffect, useState } from 'react';
import { supabase, UserDetails } from '@/utils/supabase';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/components/ui/use-toast';

// Common timezones
const COMMON_TIMEZONES = [
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Anchorage',
  'America/Adak',
  'Pacific/Honolulu',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Europe/Moscow',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Asia/Singapore',
  'Australia/Sydney',
  'Pacific/Auckland',
] as const;

interface PreferencesPanelProps {
  userId: string;
}

export default function PreferencesPanel({ userId }: PreferencesPanelProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [preferences, setPreferences] = useState<UserDetails | null>(null);
  const [workingDays, setWorkingDays] = useState({
    monday: true,
    tuesday: true,
    wednesday: true,
    thursday: true,
    friday: true,
    saturday: false,
    sunday: false,
  });
  const { toast } = useToast();

  // Get user's timezone
  const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  useEffect(() => {
    const fetchPreferences = async () => {
      try {
        const { data, error } = await supabase
          .from('user_details')
          .select('*')
          .eq('user_id', userId)
          .single();

        if (error) throw error;
        setPreferences(data);
        
        // Parse working days from metadata if available
        if (data.metadata?.working_days) {
          setWorkingDays(data.metadata.working_days);
        }
      } catch (err) {
        toast({
          title: 'Error',
          description: 'Failed to load preferences',
          variant: 'destructive',
        });
      } finally {
        setLoading(false);
      }
    };

    fetchPreferences();
  }, [userId, toast]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const { error } = await supabase
        .from('user_details')
        .update({
          ...preferences,
          metadata: {
            ...preferences?.metadata,
            working_days: workingDays,
            timezone: userTimezone,
          },
        })
        .eq('user_id', userId);

      if (error) throw error;

      toast({
        title: 'Success',
        description: 'Preferences saved successfully',
      });
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to save preferences',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <Card>
        <CardHeader>
          <CardTitle>Preferences</CardTitle>
          <CardDescription>Configure your working hours and meeting settings</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6">
            {/* Working Hours */}
            <div className="grid gap-4">
              <h3 className="text-lg font-medium">Working Hours</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="start-time">Start Time</Label>
                  <Input
                    id="start-time"
                    type="time"
                    value={preferences?.working_hours_start || '09:00'}
                    onChange={(e) =>
                      setPreferences((prev) => ({
                        ...prev!,
                        working_hours_start: e.target.value,
                      }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="end-time">End Time</Label>
                  <Input
                    id="end-time"
                    type="time"
                    value={preferences?.working_hours_end || '17:00'}
                    onChange={(e) =>
                      setPreferences((prev) => ({
                        ...prev!,
                        working_hours_end: e.target.value,
                      }))
                    }
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="timezone">Time Zone</Label>
                <Select
                  value={preferences?.metadata?.timezone || userTimezone}
                  onValueChange={(value: string) =>
                    setPreferences((prev) => ({
                      ...prev!,
                      metadata: {
                        ...prev?.metadata,
                        timezone: value,
                      },
                    }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select time zone" />
                  </SelectTrigger>
                  <SelectContent>
                    {COMMON_TIMEZONES.map((tz) => (
                      <SelectItem key={tz} value={tz}>
                        {tz}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Meeting Settings */}
            <div className="grid gap-4">
              <h3 className="text-lg font-medium">Meeting Settings</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="duration">Default Duration (minutes)</Label>
                  <Select
                    value={preferences?.meeting_duration?.toString() || '60'}
                    onValueChange={(value: string) =>
                      setPreferences((prev) => ({
                        ...prev!,
                        meeting_duration: parseInt(value),
                      }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select duration" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="15">15 minutes</SelectItem>
                      <SelectItem value="30">30 minutes</SelectItem>
                      <SelectItem value="45">45 minutes</SelectItem>
                      <SelectItem value="60">1 hour</SelectItem>
                      <SelectItem value="90">1.5 hours</SelectItem>
                      <SelectItem value="120">2 hours</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="buffer">Buffer Time (minutes)</Label>
                  <Select
                    value={preferences?.buffer_time?.toString() || '15'}
                    onValueChange={(value: string) =>
                      setPreferences((prev) => ({
                        ...prev!,
                        buffer_time: parseInt(value),
                      }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select buffer time" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">No buffer</SelectItem>
                      <SelectItem value="5">5 minutes</SelectItem>
                      <SelectItem value="10">10 minutes</SelectItem>
                      <SelectItem value="15">15 minutes</SelectItem>
                      <SelectItem value="30">30 minutes</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* Working Days */}
            <div className="grid gap-4">
              <h3 className="text-lg font-medium">Working Days</h3>
              <div className="grid grid-cols-2 gap-4">
                {Object.entries(workingDays).map(([day, enabled]) => (
                  <div key={day} className="flex items-center space-x-2">
                    <Switch
                      id={day}
                      checked={enabled}
                      onCheckedChange={(checked: boolean) =>
                        setWorkingDays((prev) => ({
                          ...prev,
                          [day]: checked,
                        }))
                      }
                    />
                    <Label htmlFor={day} className="capitalize">
                      {day}
                    </Label>
                  </div>
                ))}
              </div>
            </div>

            {/* Save Button */}
            <div className="flex justify-end">
              <Button onClick={handleSave} disabled={saving}>
                {saving ? 'Saving...' : 'Save Preferences'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
} 