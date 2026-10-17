import test from 'node:test';
import assert from 'node:assert/strict';
import {cameraFitDistance,initialCameraObject} from '../src/lib/model-camera.ts';
test('wide viewport frames closer than the old three-radius overview while fitting the target',()=>{
 const radius=100, fov=Math.PI/3;
 const distance=cameraFitDistance(radius,fov,1.6);
 assert.ok(distance<3*radius);assert.ok(distance>radius/Math.sin(fov/2));
});
test('portrait viewport increases range to fit horizontal FOV instead of cropping',()=>{
 const radius=100,fov=Math.PI/3,aspect=.5;
 const distance=cameraFitDistance(radius,fov,aspect);
 assert.ok(distance>cameraFitDistance(radius,fov,1.6));
 const visibleHalfAngle=Math.atan(Math.tan(fov/2)*aspect);
 assert.ok(Math.asin(radius/distance)<visibleHalfAngle);
});
test('invalid or temporarily zero bounds/viewport produce finite positive fallback',()=>{
 for(const radius of [0,-5,NaN,Infinity])assert.ok(Number.isFinite(cameraFitDistance(radius,undefined,0)));
 assert.ok(cameraFitDistance(1,0,-1)>0);
});
test('initial focus uses only one unambiguous local representative; explicit deep link wins',()=>{
 const links=[{object_key:'representative'}];const original=JSON.stringify(links);
 assert.equal(initialCameraObject(undefined,'LOCAL',links),'representative');
 assert.equal(initialCameraObject('unmapped-click','LOCAL',links),'unmapped-click');
 assert.equal(initialCameraObject(undefined,'LOCAL',[]),null);
 assert.equal(initialCameraObject(undefined,'LOCAL',[...links,...links]),null);
 assert.equal(initialCameraObject(undefined,'MANUAL_PLACEMENT',links),null);
 assert.equal(JSON.stringify(links),original);
});
