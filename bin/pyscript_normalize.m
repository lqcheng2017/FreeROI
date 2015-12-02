fprintf(1,'Executing %s at %s:\n',mfilename,datestr(now));
ver,
try,
        %% Generated by nipype.interfaces.spm
        if isempty(which('spm')),
             throw(MException('SPMCheck:NotFound', 'SPM not in matlab path'));
        end
        [name, version] = spm('ver');
        fprintf('SPM version: %s Release: %s\n',name, version);
        fprintf('SPM path: %s\n', which('spm'));
        spm('Defaults','fMRI');

        if strcmp(name, 'SPM8') || strcmp(name, 'SPM12b'),
           spm_jobman('initcfg');
           spm_get_defaults('CmdLine', 1);
        end

        jobs{1}.spm.spatial.normalise.estwrite.roptions.prefix = 'w';
jobs{1}.spm.spatial.normalise.estwrite.roptions.vox(1) = 1.33000004292;
jobs{1}.spm.spatial.normalise.estwrite.roptions.vox(2) = 1.0;
jobs{1}.spm.spatial.normalise.estwrite.roptions.vox(3) = 1.0;
jobs{1}.spm.spatial.normalise.estwrite.roptions.bb(1,1) = -94.2361664772;
jobs{1}.spm.spatial.normalise.estwrite.roptions.bb(1,2) = -163.873321533;
jobs{1}.spm.spatial.normalise.estwrite.roptions.bb(1,3) = -151.197623447;
jobs{1}.spm.spatial.normalise.estwrite.roptions.bb(2,1) = 89.0496043265;
jobs{1}.spm.spatial.normalise.estwrite.roptions.bb(2,2) = 140.544567563;
jobs{1}.spm.spatial.normalise.estwrite.roptions.bb(2,3) = 152.982274789;
jobs{1}.spm.spatial.normalise.estwrite.eoptions.template = {...
'/nfs/j3/userhome/zhouguangfu/Desktop/PycharmProjects/FreeROI/bin/temp_T1_brain.nii,1';...
};
jobs{1}.spm.spatial.normalise.estwrite.subj.source = {...
'/nfs/j3/userhome/zhouguangfu/workingdir/flirt/brain/freeroi/std.nii,1';...
};
jobs{1}.spm.spatial.normalise.estwrite.subj.resample = {...
'/nfs/j3/userhome/zhouguangfu/workingdir/flirt/brain/freeroi/std.nii,1';...
};

        spm_jobman('run', jobs);

        
,catch ME,
fprintf(2,'MATLAB code threw an exception:\n');
fprintf(2,'%s\n',ME.message);
if length(ME.stack) ~= 0, fprintf(2,'File:%s\nName:%s\nLine:%d\n',ME.stack.file,ME.stack.name,ME.stack.line);, end;
end;