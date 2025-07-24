// SETUP INSTRUCTIONS:
// 1. Install dependencies:
//    npm install next @prisma/client prisma dotenv
//    npm install --save-dev @types/node
//
// 2. Create a .env.local file in your project root with:
//    LINKEDIN_CLIENT_ID=your_linkedIn_client_id
//    LINKEDIN_CLIENT_SECRET=your_linkedIn_client_secret
//    LINKEDIN_REDIRECT_URI=http://localhost:3000/api/callback/linkedin
//    DATABASE_URL=your_prisma_database_url
//
// 3. Make sure the redirect URI is whitelisted in your LinkedIn developer portal.
// 4. Run: npx prisma generate && npx prisma migrate dev --name init
// 5. Start your app: npm run dev

import { prisma } from '@/lib/prisma';
import { NextResponse } from 'next/server';
import { type NextRequest } from 'next/server';

export async function GET(request: NextRequest) {
  const userId = request.nextUrl.searchParams.get('userId');
  
  if (!userId) {
    return NextResponse.json(
      { error: 'User ID is required' },
      { status: 400 }
    );
  }

  const authUrl = `https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=${process.env.LINKEDIN_CLIENT_ID}&redirect_uri=${process.env.LINKEDIN_REDIRECT_URI}&scope=openid,profile,email,w_member_social&state=${userId}`;
  
  return NextResponse.redirect(authUrl);
}

export async function POST(request: NextRequest) {
  try {
    const { code, userId } = await request.json();
    
    if (!code || !userId) {
      return NextResponse.json(
        { error: 'Code and User ID are required' },
        { status: 400 }
      );
    }

    // Exchange code for token
    const params = new URLSearchParams();
    params.append('grant_type', 'authorization_code');
    params.append('code', code);
    params.append('redirect_uri', process.env.LINKEDIN_REDIRECT_URI!);
    params.append('client_id', process.env.LINKEDIN_CLIENT_ID!);
    params.append('client_secret', process.env.LINKEDIN_CLIENT_SECRET!);
    
    const tokenResponse = await fetch('https://www.linkedin.com/oauth/v2/accessToken', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: params
    });
    
    const tokenData = await tokenResponse.json();
    console.log("Token Data:", tokenData);
    if (!tokenResponse.ok) {
      throw new Error('Failed to get access token: ' + JSON.stringify(tokenData));
    }
    
    const { access_token, expires_in, refresh_token } = tokenData;
    
    // Get LinkedIn profile information
    const profileResponse = await fetch('https://api.linkedin.com/v2/me', {
      headers: {
        'Authorization': `Bearer ${access_token}`,
        'Connection': 'Keep-Alive',
      }
    });
    
    if (!profileResponse.ok) {
      throw new Error('Failed to get LinkedIn profile');
    }
    
    const profileData = await profileResponse.json();
    const platformUserId = profileData.id;
    const platformUsername = profileData.name || profileData.localizedFirstName;
    
    // Update or create the social account using upsert
    await prisma.socialAccount.upsert({
      where: {
        userId_platform: {
          userId: userId,
          platform: 'LINKEDIN'
        }
      },
      update: {
        accessToken: access_token,
        refreshToken: refresh_token || null,
        tokenExpiresAt: new Date(Date.now() + expires_in * 1000),
        platformUserId: platformUserId,
        platformUsername: platformUsername,
        isConnected: true
      },
      create: {
        platform: 'LINKEDIN',
        accessToken: access_token,
        refreshToken: refresh_token || null,
        tokenExpiresAt: new Date(Date.now() + expires_in * 1000),
        platformUserId: platformUserId,
        platformUsername: platformUsername,
        userId: userId,
        isConnected: true
      }
    });
    
    // Use absolute URL for redirect
    const dashboardUrl = new URL('/dashboard', request.nextUrl.origin);
    dashboardUrl.searchParams.set('linkedin', 'connected');
    
    return NextResponse.redirect(dashboardUrl.toString());
  } catch (error) {
    console.error('LinkedIn auth error:', error);
    
    // Use absolute URL for error redirect
    const errorUrl = new URL('/auth/error', request.nextUrl.origin);
    errorUrl.searchParams.set(
      'message', 
      error instanceof Error ? error.message : 'Authentication failed'
    );
    
    return NextResponse.redirect(errorUrl.toString());
  }
}

// Ensure other HTTP methods are not allowed
export async function PUT() {
  return NextResponse.json({ error: 'Method not allowed' }, { status: 405 });
}
export async function DELETE() {
  return NextResponse.json({ error: 'Method not allowed' }, { status: 405 });
}
export async function PATCH() {
  return NextResponse.json({ error: 'Method not allowed' }, { status: 405 });
}