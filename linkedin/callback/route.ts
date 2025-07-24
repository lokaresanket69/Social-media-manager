// app/api/social-accounts/linkedin/callback/route.ts
import { NextResponse } from 'next/server';
import { type NextRequest } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get('code');
  const state = searchParams.get('state'); // Contains your user ID

  if (!code) {
    const errorUrl = new URL('/auth/error', request.nextUrl.origin);
    errorUrl.searchParams.set('message', 'missing_code');
    return NextResponse.redirect(errorUrl.toString());
  }

  try {
    // 1. Exchange code for token
    const tokenRes = await fetch('https://www.linkedin.com/oauth/v2/accessToken', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code,
        redirect_uri: process.env.LINKEDIN_REDIRECT_URI!,
        client_id: process.env.LINKEDIN_CLIENT_ID!,
        client_secret: process.env.LINKEDIN_CLIENT_SECRET!,
      }),
    });

    const tokenData = await tokenRes.json();

    if (!tokenRes.ok) {
      throw new Error(`Token exchange failed: ${tokenData.error_description || tokenData.error}`);
    }

    // 2. Fetch LinkedIn profile
    const profileRes = await fetch('https://api.linkedin.com/v2/userinfo', {
      headers: { 
        'Authorization': `Bearer ${tokenData.access_token}`,
        'Connection': 'Keep-Alive' 
      },
    });
    
    if (!profileRes.ok) {
      throw new Error('Failed to fetch LinkedIn profile');
    }
    
    const profile = await profileRes.json();

    console.log('LinkedIn profile:', profile);

    // 3. Save to database if you have a user ID in state
    if (state) {
      try {
        // Check if social account already exists
        const existingAccount = await prisma.socialAccount.findFirst({
          where: {
            userId: state,
            platform: 'LINKEDIN'
          }
        });

        // Update or create the social account
        if (existingAccount) {
          await prisma.socialAccount.update({
            where: {
              id: existingAccount.id
            },
            data: {
              accessToken: tokenData.access_token,
              refreshToken: tokenData.refresh_token || null,
              tokenExpiresAt: new Date(Date.now() + tokenData.expires_in * 1000),
              platformUserId: profile.sub,
              platformUsername: profile.name || profile.given_name,
              isConnected: true
            }
          });
        } else {
          await prisma.socialAccount.create({
            data: {
              platform: 'LINKEDIN',
              accessToken: tokenData.access_token,
              refreshToken: tokenData.refresh_token || null,
              tokenExpiresAt: new Date(Date.now() + tokenData.expires_in * 1000),
              platformUserId: profile.sub,
              platformUsername: profile.name || profile.given_name,
              userId: state,
              isConnected: true
            }
          });
        }
      } catch (dbError) {
        console.error('Database error:', dbError);
        // Continue to redirect even if DB save fails
      }
    }

    // Use absolute URL for redirect
    const dashboardUrl = new URL('/dashboard', request.nextUrl.origin);
    dashboardUrl.searchParams.set('linkedin', 'connected');
    return NextResponse.redirect(dashboardUrl.toString());
  } catch (error) {
    console.error('LinkedIn callback error:', error);
    
    // Use absolute URL for error redirect
    const errorUrl = new URL('/auth/error', request.nextUrl.origin);
    errorUrl.searchParams.set(
      'message', 
      error instanceof Error ? error.message : 'Unknown error'
    );
    return NextResponse.redirect(errorUrl.toString());
  }
}