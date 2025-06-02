import { useEffect, useState } from 'react';
import { supabase, Contact, Message, UserDetails } from '@/utils/supabase';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { formatDistanceToNow } from 'date-fns';

interface ContactWithMessages extends Contact {
  messages: Message[];
}

interface DashboardProps {
  userId: string;
}

export default function Dashboard({ userId }: DashboardProps) {
  const [contacts, setContacts] = useState<ContactWithMessages[]>([]);
  const [userDetails, setUserDetails] = useState<UserDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch user preferences
        const { data: preferences, error: prefError } = await supabase
          .from('user_details')
          .select('*')
          .eq('user_id', userId)
          .single();

        if (prefError) throw prefError;
        setUserDetails(preferences);

        // Fetch recent contacts with their messages
        const { data: recentContacts, error: contactsError } = await supabase
          .from('contacts')
          .select('*, messages(*)')
          .order('created_at', { ascending: false })
          .limit(10);

        if (contactsError) throw contactsError;
        setContacts(recentContacts || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    // Subscribe to real-time updates
    const messagesSubscription = supabase
      .channel('messages')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'messages' }, 
        (payload) => {
          // Update contacts list when new messages arrive
          fetchData();
        }
      )
      .subscribe();

    return () => {
      messagesSubscription.unsubscribe();
    };
  }, [userId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-red-600">Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="grid gap-6">
        {/* User Preferences Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Your Preferences</CardTitle>
            <CardDescription>Current working hours and meeting settings</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium">Working Hours</p>
                <p className="text-sm text-gray-500">
                  {userDetails?.working_hours_start} - {userDetails?.working_hours_end}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium">Meeting Duration</p>
                <p className="text-sm text-gray-500">{userDetails?.meeting_duration} minutes</p>
              </div>
              <div>
                <p className="text-sm font-medium">Buffer Time</p>
                <p className="text-sm text-gray-500">{userDetails?.buffer_time} minutes</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recent Interactions */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Interactions</CardTitle>
            <CardDescription>Latest conversations with contacts</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="all">
              <TabsList>
                <TabsTrigger value="all">All</TabsTrigger>
                <TabsTrigger value="today">Today</TabsTrigger>
                <TabsTrigger value="week">This Week</TabsTrigger>
              </TabsList>
              <TabsContent value="all" className="mt-4">
                <ScrollArea className="h-[400px]">
                  {contacts.map((contact) => (
                    <div key={contact.id} className="flex items-start space-x-4 p-4 border-b last:border-0">
                      <Avatar>
                        <AvatarImage src={`https://ui-avatars.com/api/?name=${contact.name}`} />
                        <AvatarFallback>{contact.name?.charAt(0) || '?'}</AvatarFallback>
                      </Avatar>
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium">{contact.name || 'Unknown'}</p>
                          <Badge variant="outline">
                            {formatDistanceToNow(new Date(contact.created_at), { addSuffix: true })}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-500">
                          {contact.email || contact.telegram_id || 'No contact info'}
                        </p>
                        {contact.messages && contact.messages.length > 0 && (
                          <p className="text-sm text-gray-600 line-clamp-2">
                            {contact.messages[0].content}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </ScrollArea>
              </TabsContent>
              <TabsContent value="today" className="mt-4">
                {/* Filter contacts for today */}
                <ScrollArea className="h-[400px]">
                  {contacts
                    .filter((contact) => {
                      const today = new Date();
                      const contactDate = new Date(contact.created_at);
                      return contactDate.toDateString() === today.toDateString();
                    })
                    .map((contact) => (
                      <div key={contact.id} className="flex items-start space-x-4 p-4 border-b last:border-0">
                        <Avatar>
                          <AvatarImage src={`https://ui-avatars.com/api/?name=${contact.name}`} />
                          <AvatarFallback>{contact.name?.charAt(0) || '?'}</AvatarFallback>
                        </Avatar>
                        <div className="flex-1 space-y-1">
                          <div className="flex items-center justify-between">
                            <p className="text-sm font-medium">{contact.name || 'Unknown'}</p>
                            <Badge variant="outline">
                              {formatDistanceToNow(new Date(contact.created_at), { addSuffix: true })}
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-500">
                            {contact.email || contact.telegram_id || 'No contact info'}
                          </p>
                          {contact.messages && contact.messages.length > 0 && (
                            <p className="text-sm text-gray-600 line-clamp-2">
                              {contact.messages[0].content}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                </ScrollArea>
              </TabsContent>
              <TabsContent value="week" className="mt-4">
                {/* Filter contacts for this week */}
                <ScrollArea className="h-[400px]">
                  {contacts
                    .filter((contact) => {
                      const today = new Date();
                      const contactDate = new Date(contact.created_at);
                      const diffTime = Math.abs(today.getTime() - contactDate.getTime());
                      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                      return diffDays <= 7;
                    })
                    .map((contact) => (
                      <div key={contact.id} className="flex items-start space-x-4 p-4 border-b last:border-0">
                        <Avatar>
                          <AvatarImage src={`https://ui-avatars.com/api/?name=${contact.name}`} />
                          <AvatarFallback>{contact.name?.charAt(0) || '?'}</AvatarFallback>
                        </Avatar>
                        <div className="flex-1 space-y-1">
                          <div className="flex items-center justify-between">
                            <p className="text-sm font-medium">{contact.name || 'Unknown'}</p>
                            <Badge variant="outline">
                              {formatDistanceToNow(new Date(contact.created_at), { addSuffix: true })}
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-500">
                            {contact.email || contact.telegram_id || 'No contact info'}
                          </p>
                          {contact.messages && contact.messages.length > 0 && (
                            <p className="text-sm text-gray-600 line-clamp-2">
                              {contact.messages[0].content}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                </ScrollArea>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
} 